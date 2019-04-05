import numpy as np
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.core import msg
from xicam.core.data import load_header, NonDBHeader

from xicam.plugins import GUIPlugin, GUILayout, manager as pluginmanager
from .pythontools.toolswidget import AdvancedPythonWidget
from .controlwidgets.BCSConnector import BCSConnector
from .controlwidgets.devicelist import DeviceList

from .runengine import RE


class AcquirePlugin(GUIPlugin):
    name = 'Acquire'
    sigLog = Signal(int, str, str, np.ndarray)

    def __init__(self):
        devicelist = DeviceList()
        controlsstack = QStackedWidget()
        devicelist.sigShowControl.connect(controlsstack.addSetWidget)

        self.stages = {'Controls': GUILayout(controlsstack,
                                             left=devicelist,
                                             ),
                       'Bluesky': GUILayout(AdvancedPythonWidget(),
                                            left=devicelist),
                       }
        super(AcquirePlugin, self).__init__()


class QStackedWidget(QStackedWidget):
    def addSetWidget(self, w):
        self.addWidget(w)
        self.setCurrentWidget(w)
