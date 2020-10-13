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
from xicam.gui.widgets.imageviewmixins import PixelCoordinates, Crosshair, BetterButtons, LogScaleIntensity, ImageViewHistogramOverflowFix
from caproto._utils import CaprotoTimeoutError
from ophyd.signal import ConnectionTimeoutError
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.pushbutton import PyDMPushButton
from bluesky.plans import count
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

    def __init__(self, device, maxfps=1):
        super(AreaDetectorController, self).__init__(device)
        self.maxfps = maxfps
        self._autolevel = True

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

        self._last_timestamp = time.time()

        self.thread = threads.QThreadFutureIterator(self.update,
                                                    showBusy=False,
                                                    callback_slot=self.setFrame,
                                                    except_slot=self.setError,
                                                    threadkey=f'device-updater-{self.device.name}')
        self.thread.start()

    def update(self):

        while True:
            try:
                if not self.device.connected:
                    with msg.busyContext():
                        msg.showMessage('Connecting to device...')
                        self.device.wait_for_connection()

                # Do nothing unless this widget is visible
                if not self.visibleRegion().isEmpty():
                    # # check if the object thinks its staged or is actually not staged
                    # if not self.device.trigger_staged or \
                    #         self.device.image1.array_size.get() == (0, 0, 0):
                    #     msg.showMessage('Staging the device...')
                    #     self.device.trigger()

                    yield self.getFrame()

            except (RuntimeError, CaprotoTimeoutError, ConnectionTimeoutError, TimeoutError) as ex:
                threads.invoke_in_main_thread(self.error_text.setText, 'An error occurred communicating with this device.')
                msg.logError(ex)

            time.sleep(1./self.maxfps)

    def getFrame(self):
        try:
            if not self.passive.isChecked():
                self.device.trigger()
            data = self.device.image1.shaped_image.get()
            # TODO: apply corrections to display; requires access to flats and darks
            # data = np.squeeze(CorrectFastCCDImage().asfunction(images=data,)['corrected_images'].value)
            return data
        except (RuntimeError, CaprotoTimeoutError, ConnectionTimeoutError) as ex:
            threads.invoke_in_main_thread(self.error_text.setText, 'An error occurred communicating with this device.')
            msg.logError(ex)
        return None

    def setFrame(self, image, *args, **kwargs):
        if image is not None:
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

    def setError(self, exception: Exception):
        msg.logError(exception)
        self.error_text.setText('An error occurred while connecting to this device.')

    def acquire(self):
        get_run_engine()(count([self.device]))


# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
