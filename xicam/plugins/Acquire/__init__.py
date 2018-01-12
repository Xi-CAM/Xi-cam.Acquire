import numpy as np
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.core import msg
from xicam.core.data import load_header, NonDBHeader

from xicam.plugins import GUIPlugin, GUILayout, manager as pluginmanager
from .pythontools.toolswidget import AdvancedPythonWidget
from .controlwidgets.BCSConnector import BCSConnector


class AcquirePlugin(GUIPlugin):
    name = 'Acquire'
    sigLog = Signal(int, str, str, np.ndarray)

    def __init__(self):
        self.stages = {'Controls': GUILayout(QWidget(), leftbottom=BCSConnector()),
                       'Scripting': GUILayout(AdvancedPythonWidget()),
                       }
        super(AcquirePlugin, self).__init__()

    def appendHeader(self, doc: NonDBHeader, **kwargs):
        self.stages['Calibrate'].centerwidget.setHeader(doc)
