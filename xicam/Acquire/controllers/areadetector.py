import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
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


class ADImageView(DynImageView,
                  PixelCoordinates,
                  Crosshair,
                  BetterButtons,
                  # LogScaleIntensity,
                  ImageViewHistogramOverflowFix):
    pass


class AreaDetectorController(ControllerPlugin):
    viewclass = ADImageView

    def __init__(self, device, maxfps=10):
        super(AreaDetectorController, self).__init__(device)
        self.maxfps = maxfps
        self._autolevel = True
        self.RE = get_run_engine()

        self.setLayout(QVBoxLayout())

        self.imageview = self.viewclass()
        self.passive = QCheckBox('Passive Mode')
        self.passive.setChecked(True)
        self.error_text = pg.TextItem('Connecting to device...')
        self.imageview.view.addItem(self.error_text)
        self.layout().addWidget(self.imageview)
        self.layout().addWidget(self.passive)

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

        acquire_layout = QVBoxLayout()
        acquire_button = QPushButton('Acquire')
        acquire_button.clicked.connect(self.acquire)
        acquire_layout.addWidget(acquire_button)
        acquire_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.cam.initialize.setpoint_pvname}',
                           label='Initialize'))
        acquire_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.cam.shutdown.setpoint_pvname}', label='Shutdown'))

        acquire_panel = QGroupBox('Acquire')
        acquire_panel.setLayout(acquire_layout)

        hlayout = QHBoxLayout()

        hlayout.addWidget(config_panel)
        hlayout.addWidget(acquire_panel)
        self.layout().addLayout(hlayout)

        # WIP
        # self.lutCheck = QCheckBox()
        # self.LUT = GradientWidget()
        # self.downsampleCheck = QCheckBox()
        # self.scaleCheck = QCheckBox()
        # self.rgbLevelsCheck = QCheckBox()

        self.thread = None
        self._last_timestamp = time.time()

        self.device.image1.shaped_image.subscribe(partial(threads.invoke_in_main_thread, self.setFrame))

        self.passive.toggled.connect(self.setPassive)

    def update(self):
        self.thread = threads.QThreadFuture(self.getFrame, showBusy=False,
                                            callback_slot=partial(self.setFrame, autoLevels=self._autolevel),
                                            except_slot=self.setError)
        self.thread.start()

    def _trigger_thread(self):
        while True:
            while 1. / (time.time() - self._last_timestamp) > self.maxfps:
                time.sleep(1. / self.maxfps)

            if self.passive.isChecked() or self.visibleRegion().isEmpty():
                break

            try:
                if not self.device.connected:
                    with msg.busyContext():
                        msg.showMessage('Connecting to device...')
                        self.device.wait_for_connection()

                self.device.device_obj.trigger()
            except (RuntimeError, CaprotoTimeoutError, ConnectionTimeoutError, TimeoutError) as ex:
                threads.invoke_in_main_thread(self.error_text.setText,
                                              'An error occurred communicating with this device.')
                msg.logError(ex)

    def setPassive(self, passive):
        if passive:
            if self.thread:
                self.thread.cancel()
                self.thread = None
        else:
            self.thread = threads.QThreadFuture(self._trigger_thread,
                                                except_slot=lambda ex: self.device.device_obj.unstage())
            self.thread.start()

    def getFrame(self):
        try:
            if not self.passive.isChecked():
                self.device.device_obj.trigger()
            return self.device.device_obj.image1.shaped_image.get()
        except (RuntimeError, CaprotoTimeoutError) as ex:
            msg.logError(ex)
        return None

    def setFrame(self, value=None, **kwargs):
        image = value

        if image is None:
            return

        # # Never exceed maxfps
        # if 1. / (time.time() - self._last_timestamp) > self.maxfps:
        #     return

        if self.imageview.image is None:
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

        self.error_text.setText(f'FPS: {1. / (time.time() - self._last_timestamp):.2f}')
        self._last_timestamp = time.time()

        # self.timer.singleShot(1. / self.maxfps * 1000, self.update)

    def setError(self, exception: Exception):
        msg.logError(exception)
        self.error_text.setText('An error occurred while connecting to this device.')

    def acquire(self):
        self.RE(count([self.device]))


# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
