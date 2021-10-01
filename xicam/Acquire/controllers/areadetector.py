import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
from PyQt5.QtWidgets import QProgressBar
from pyqtgraph import GradientWidget
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout, QHBoxLayout, QPushButton
from qtpy.QtCore import QTimer
from xicam.core import threads
from xicam.plugins import ControllerPlugin
from functools import partial
from xicam.core import msg
from xicam.gui.widgets.dynimageview import DynImageView
from xicam.gui.widgets.imageviewmixins import PixelCoordinates, Crosshair, BetterButtons, LogScaleIntensity, \
    ImageViewHistogramOverflowFix
from caproto._utils import CaprotoTimeoutError
from ophyd.signal import ConnectionTimeoutError
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.pushbutton import PyDMPushButton
from bluesky.plans import count
import ophyd
from xicam.Acquire.runengine import RE
from timeit import default_timer
from contextlib import contextmanager
# from xicam.SAXS.processing.correction import CorrectFastCCDImage
from xicam.Acquire.runengine import get_run_engine
import time

from typing import Callable


class ADImageView(DynImageView,
                  PixelCoordinates,
                  Crosshair,
                  BetterButtons,
                  LogScaleIntensity,
                  ImageViewHistogramOverflowFix):
    pass


class AreaDetectorController(ControllerPlugin):
    viewclass = ADImageView

    def __init__(self, device, preprocess_enabled=True, maxfps=4):  # Note: typical query+processing+display <.2s
        super(AreaDetectorController, self).__init__(device)
        self.maxfps = maxfps
        self.preprocess_enabled = preprocess_enabled
        self._autolevel = True
        self.RE = get_run_engine()

        self.setLayout(QVBoxLayout())

        self.coupled_devices = []

        self.getting_frame = False

        self.bg_correction = QCheckBox("Background Correction")
        self.bg_correction.setChecked(True)

        self.imageview = self.viewclass()
        self.passive = QCheckBox('Passive Mode')
        self.passive.setChecked(True)
        self.error_text = pg.TextItem('Waiting for data...')
        self.imageview.view.addItem(self.error_text)
        self.layout().addWidget(self.imageview)
        self.layout().addWidget(self.bg_correction)
        self.layout().addWidget(self.passive)
        self.metadata = {}

        config_layout = QFormLayout()
        config_layout.addRow('Acquire Time',
                             PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_time.setpoint_pvname}'))
        config_layout.addRow('Acquire Period',
                             PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_period.setpoint_pvname}'))
        config_layout.addRow('Number of Images',
                             PyDMLineEdit(init_channel=f'ca://{device.hdf5.num_capture.setpoint_pvname}'))
        config_layout.addRow('Number of Exposures',
                             PyDMLineEdit(init_channel=f'ca://{device.cam.num_exposures.setpoint_pvname}'))
        # config_layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.image_mode.setpoint_pvname}'))
        # config_layout.addRow('Trigger Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.trigger_mode.setpoint_pvname}'))

        config_panel = QGroupBox('Configuration')
        config_panel.setLayout(config_layout)

        # Create the Acquire panel and its buttons
        acquire_layout = QVBoxLayout()
        acquire_button = QPushButton('Acquire')
        self.acquire_progress = QProgressBar()
        acquire_button.clicked.connect(self.acquire)
        acquire_layout.addWidget(acquire_button)
        acquire_layout.addWidget(self.acquire_progress)

        self.abort_button = QPushButton('Abort')
        self.abort_button.clicked.connect(self.abort)
        self._ready()  # prepare the appropriate abort btn check state and styling

        acquire_layout.addWidget(self.abort_button)

        acquire_panel = QGroupBox('Acquire')
        acquire_panel.setLayout(acquire_layout)

        self.hlayout = QHBoxLayout()

        self.hlayout.addWidget(config_panel)
        self.hlayout.addWidget(acquire_panel)
        self.layout().addLayout(self.hlayout)

        # Connect relevant RE signals to update abort btn check state and styling depending on the RE state
        self.RE.sigStart.connect(self._started)
        self.RE.sigReady.connect(self._ready)

        # WIP
        # self.lutCheck = QCheckBox()
        # self.LUT = GradientWidget()
        # self.downsampleCheck = QCheckBox()
        # self.scaleCheck = QCheckBox()
        # self.rgbLevelsCheck = QCheckBox()

        self.thread = None
        self._last_timestamp = time.time()
        # self.update_timer = QTimer()
        # self.update_timer.setInterval(1000 // maxfps)
        # self.update_timer.timeout.connect(self.updateFrame)
        # self.update_timer.start()

        # self.device.image1.shaped_image.subscribe(self.cacheFrame, 'value')

        self.setPassive(True)
        self.passive.toggled.connect(self.setPassive)

    def _update_thread(self, update_action:Callable):
        while True:
            if not self.passive.isChecked():
                break

            if self.visibleRegion().isEmpty():
                time.sleep(1 / self.maxfps)
                continue

            try:
                if not self.device.connected:
                    with msg.busyContext():
                        msg.showMessage('Connecting to device...')
                        self.device.wait_for_connection()

                update_action()
            except (RuntimeError, CaprotoTimeoutError, ConnectionTimeoutError, TimeoutError) as ex:
                threads.invoke_in_main_thread(self.error_text.setText,
                                              'An error occurred communicating with this device.')
                msg.logError(ex)
            except Exception as e:
                threads.invoke_in_main_thread(self.error_text.setText,
                                              'Unknown error occurred when attempting to communicate with device.')
                msg.logError(e)

            num_exposures_counter = self.device.cam.num_exposures_counter.get()
            num_exposures = self.device.cam.num_exposures.get()
            num_captured = self.device.hdf5.num_captured.get()
            num_capture = self.device.hdf5.num_capture.get()
            capturing = self.device.hdf5.capture.get()
            if capturing:
                current = num_exposures_counter + num_captured * num_exposures
                total = num_exposures * num_capture
            elif num_exposures == 1:  # Show 'busy' for just one exposure
                current = 0
                total = 0
            else:
                current = num_exposures_counter
                total = num_exposures
            threads.invoke_in_main_thread(self._update_progress, current, total)

            while self.getting_frame:
                time.sleep(.01)

            t = time.time()
            max_period = 1 / self.maxfps
            current_elapsed = t - self._last_timestamp

            if current_elapsed < max_period:
                time.sleep(max_period - current_elapsed)

            self._last_timestamp = time.time()

    def _update_progress(self, current, total):
        self.acquire_progress.setMaximum(total)
        self.acquire_progress.setValue(current)

    def setPassive(self, passive):
        if self.thread:
            self.thread.cancel()
            self.thread = None

        if passive:
            update_action = self.updateFrame
        else:
            update_action = self.device.trigger

        self.thread = threads.QThreadFuture(self._update_thread, update_action, showBusy=False,
                                            except_slot=lambda ex: self.device.unstage())
        self.thread.start()

    def cacheFrame(self, value, **_):
        self.cached_frame = value

    def updateFrame(self):
        image = self.device.image1.shaped_image.get()
        if image is not None and len(image):
            try:
                image = self.preprocess(image)
            except Exception as ex:
                pass
                # msg.logError(ex)
            self.getting_frame = True
            threads.invoke_in_main_thread(self._setFrame, image)

    def _setFrame(self, image):

        if self.imageview.image is None and len(image):
            self.imageview.setImage(image, autoHistogramRange=True, autoLevels=True)
        else:
            self.imageview.imageDisp = None
            self.error_text.setText('')
            self.imageview.image = image
            # self.imageview.updateImage(autoHistogramRange=kwargs['autoLevels'])
            image = self.imageview.getProcessedImage()
            if self._autolevel:
                self.imageview.ui.histogram.setHistogramRange(self.imageview.levelMin, self.imageview.levelMax)
                self.imageview.autoLevels()
            self.imageview.imageItem.updateImage(image)

            self._autolevel = False

        self.error_text.setText(f'Update time: {(time.time() - self._last_timestamp):.2f} s')
        self.getting_frame = False

    def preprocess(self, image):
        return image

    def setError(self, exception: Exception):
        msg.logError(exception)
        self.error_text.setText('An error occurred while connecting to this device.')

    def acquire(self):
        self.RE(count(self.coupled_devices), **self.metadata)

    def abort(self):
        self.RE.abort('Acquisition aborted by Xi-cam user.')

    def _started(self):
        self.abort_button.setEnabled(True)
        self.abort_button.setStyleSheet('background-color:red;color:white;font-weight:bold;')

    def _ready(self):
        self.abort_button.setEnabled(False)
        self.abort_button.setStyleSheet('')
