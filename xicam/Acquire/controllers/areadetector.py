import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
from pyqtgraph import GradientWidget
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from qtpy.QtCore import QTimer
from xicam.core import threads
from xicam.plugins import ControllerPlugin
from functools import partial


class AreaDetectorController(ControllerPlugin):
    def __init__(self, device, maxfps=30):
        super(AreaDetectorController, self).__init__(device)
        self.maxfps = maxfps
        self._autolevel = True

        self.setLayout(QVBoxLayout())

        self.imageview = pg.ImageView()
        self.layout().addWidget(self.imageview)

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

    def update(self):
        self.thread = threads.QThreadFuture(self.getFrame, showBusy=False,
                                            callback_slot=partial(self.setFrame, autoLevels=self._autolevel))
        self.thread.start()

    def getFrame(self):
        return self.device.device_obj.image1.get().shaped_image

    def setFrame(self, image, *args, **kwargs):
        self.imageview.imageDisp = None
        self.imageview.image = image
        # self.imageview.updateImage(autoHistogramRange=kwargs['autoLevels'])
        image = self.imageview.getProcessedImage()
        if kwargs['autoLevels']:
            self.imageview.ui.histogram.setHistogramRange(self.imageview.levelMin, self.imageview.levelMax)
            self.imageview.autoLevels()
        self.imageview.imageItem.updateImage(image)

        # self.imageview.setImage(image, *args, **kwargs)
        self._autolevel = False
        self.timer.singleShot(1. / self.maxfps * 1000, self.update)

# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
