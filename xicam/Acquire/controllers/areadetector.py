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
from bluesky.plans import count
from timeit import default_timer
from contextlib import contextmanager
# from xicam.SAXS.processing.correction import CorrectFastCCDImage
from xicam.Acquire.runengine import RE
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

        pvname = device.pvname
        config_layout = QFormLayout()
        config_layout.addRow('Acquire Time', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:AcquireTime'))
        config_layout.addRow('Number of Images', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumImages'))
        config_layout.addRow('Number of Exposures', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumExposures'))
        config_layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{pvname}cam1:ImageMode'))
        config_layout.addRow('Trigger Mode', PyDMEnumComboBox(init_channel=f'ca://{pvname}cam1:TriggerMode'))

        config_panel = QGroupBox('Configuration')
        config_panel.setLayout(config_layout)

        acquire_layout = QVBoxLayout()
        acquire_button = QPushButton('Acquire')
        acquire_button.clicked.connect(self.acquire)
        acquire_layout.addWidget(acquire_button)

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
        with msg.busyContext():
            msg.showMessage('Instantiating device...')
            device = self.device.device_obj  # Force cache the device_obj

            if not self.device.device_obj.trigger_staged:
                msg.showMessage('Staging the device...')
                self.device.device_obj.trigger()

        msg.showMessage('Device ready!')

        while True:
            if not self.visibleRegion().isEmpty():
                yield self.getFrame()
            time.sleep(1./self.maxfps)

    def getFrame(self):
        try:
            if not self.passive.isChecked():
                self.device.device_obj.trigger()
            data = self.device.device_obj.image1.shaped_image.get()
            # TODO: apply corrections to display; requires access to flats and darks
            # data = np.squeeze(CorrectFastCCDImage().asfunction(images=data,)['corrected_images'].value)
            return data
        except (RuntimeError, CaprotoTimeoutError, ConnectionTimeoutError) as ex:
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
        RE(count([self.device.device_obj]))


# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
