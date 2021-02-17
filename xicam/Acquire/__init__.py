from . import patches
import numpy as np
import os
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QStackedWidget

from xicam.plugins import GUIPlugin, GUILayout
from .pythontools.editor import scripteditor
from .controlwidgets.BCSConnector import BCSConnector
from .controlwidgets.deviceview import DeviceView
from .controlwidgets import RunEngineWidget

from . import runengine

#export pydm environment variable
os.environ["PYDM_DISPLAYS_PATH"] = os.path.dirname(__file__) +"/xicam/Acquire/ui/"

class AcquirePlugin(GUIPlugin):
    name = 'Acquire'
    sigLog = Signal(int, str, str, np.ndarray)

    def __init__(self):
        runengine.initialize()
        deviceviewcontainer = DeviceView()
        devicelist = deviceviewcontainer.view
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
