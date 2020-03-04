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
from caproto._utils import CaprotoTimeoutError
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from bluesky.plans import count

from xicam.Acquire.runengine import RE
import time


class AreaDetectorController(ControllerPlugin):
    viewclass = DynImageView

    def __init__(self, device, maxfps=30):
        super(AreaDetectorController, self).__init__(device)
        self.maxfps = maxfps
        self._autolevel = True

        self.setLayout(QVBoxLayout())

        self.imageview = self.viewclass()
        self.passive = QCheckBox('Passive Mode')
        self.passive.setChecked(True)
        self.error_text = pg.TextItem('')
        self.imageview.view.addItem(self.error_text)
        self.layout().addWidget(self.imageview)
        self.layout().addWidget(self.passive)

        pvname = device.pvname
        config_layout = QFormLayout()
        config_layout.addRow('Acquire Time', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:AcquireTime'))
        config_layout.addRow('Number of Images', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumImages'))
        config_layout.addRow('Number of Exposures', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumExposures'))
        config_layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{pvname}cam1:ImageMode'))

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

        self.thread = None
        self.timer = QTimer()

        partial(self.imageview.imageItem.setImage, autoLevels=False)

        # WIP
        # self.lutCheck = QCheckBox()
        # self.LUT = GradientWidget()
        # self.downsampleCheck = QCheckBox()
        # self.scaleCheck = QCheckBox()
        # self.rgbLevelsCheck = QCheckBox()

        self.timer.singleShot(1. / self.maxfps * 1000, self.update)
        self._last_timestamp = time.time()

    def update(self):
        self.thread = threads.QThreadFuture(self.getFrame, showBusy=False,
                                            callback_slot=partial(self.setFrame, autoLevels=self._autolevel),
                                            except_slot=self.setError)
        self.thread.start()

    def getFrame(self):
        try:
            if not self.passive.isChecked():
                self.device.device_obj.trigger()
            return self.device.device_obj.image1.shaped_image.get()
        except (RuntimeError, CaprotoTimeoutError) as ex:
            msg.logError(ex)
        return None

    def setFrame(self, image, *args, **kwargs):
        if image is not None:
            self.imageview.imageDisp = None
            self.error_text.setText('')
            self.imageview.image = image
            # self.imageview.updateImage(autoHistogramRange=kwargs['autoLevels'])
            image = self.imageview.getProcessedImage()
            if kwargs['autoLevels']:
                self.imageview.ui.histogram.setHistogramRange(self.imageview.levelMin, self.imageview.levelMax)
                self.imageview.autoLevels()
            self.imageview.imageItem.updateImage(image)

            # self.imageview.setImage(image, *args, **kwargs)
            self._autolevel = False

        self.error_text.setText(f'FPS: {1. / (time.time() - self._last_timestamp):.2f}')
        self._last_timestamp = time.time()

        self.timer.singleShot(1. / self.maxfps * 1000, self.update)

    def setError(self, exception: Exception):
        msg.logError(exception)
        self.error_text.setText('An error occurred while connecting to this device.')

    def acquire(self):
        RE(count([self.device.device_obj]))


# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
