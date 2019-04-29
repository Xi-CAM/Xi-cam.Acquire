import numpy as np
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.core import msg
from xicam.core.data import load_header, NonDBHeader

from xicam.plugins import GUIPlugin, GUILayout, manager as pluginmanager
from .pythontools.editor import scripteditor
from .controlwidgets.BCSConnector import BCSConnector
from .controlwidgets.devicelist import DeviceList
from .controlwidgets import RunEngineWidget

from .runengine import RE


class AcquirePlugin(GUIPlugin):
    name = 'Acquire'
    sigLog = Signal(int, str, str, np.ndarray)

    def __init__(self):
        devicelist = DeviceList()
        controlsstack = QStackedWidget()
        devicelist.sigShowControl.connect(controlsstack.addSetWidget)

        self.stages = {'Controls': GUILayout(controlsstack,
                                             left=devicelist, ),
                       'Plans': GUILayout(scripteditor(),
                                          left=devicelist),
                       'Run Engine': GUILayout(RunEngineWidget(),
                                               left=devicelist)
                       }
        super(AcquirePlugin, self).__init__()


class QStackedWidget(QStackedWidget):
    def addSetWidget(self, w):
        self.addWidget(w)
        self.setCurrentWidget(w)
