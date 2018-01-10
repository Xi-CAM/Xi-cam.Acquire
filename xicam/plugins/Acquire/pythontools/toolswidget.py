from qtpy.QtWidgets import *
from .editor import scripteditor
from .console import ipythonconsole


class AdvancedPythonWidget(QTabWidget):
    def __init__(self):
        super(AdvancedPythonWidget, self).__init__()

        self.ipythonconsole = ipythonconsole()
        self.scripteditor = scripteditor()

        self.addTab(self.ipythonconsole, 'IPython')
        self.addTab(self.scripteditor, 'Script Editor')

    def __getattr__(self, attr):  ## implicitly wrap methods from children
        for widget in [self.ipythonconsole, self.scripteditor]:
            if hasattr(widget, attr):
                m = getattr(widget, attr)
                if hasattr(m, '__call__'):
                    return m
        raise NameError(attr)
