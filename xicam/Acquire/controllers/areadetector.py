import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
from pyqtgraph import GradientWidget
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from qtpy.QtCore import QTimer
from xicam.core import threads
from xicam.plugins import ControllerPlugin
from functools import partial
from xicam.core import msg
from xicam.gui.widgets.dynimageview import DynImageView
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
        except RuntimeError as ex:
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

        msg.logMessage('fps:', 1. / (time.time() - self._last_timestamp))
        self._last_timestamp = time.time()

        self.timer.singleShot(1. / self.maxfps * 1000, self.update)

    def setError(self, exception: Exception):
        msg.logError(exception)
        self.error_text.setText('An error occurred while connecting to this device.')

# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
