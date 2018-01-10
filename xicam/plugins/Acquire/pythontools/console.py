from qtpy.QtGui import *
import qtpy
import sys

if 'PySide.QtCore' in sys.modules and qtpy.API != 'pyside': del sys.modules['PySide.QtCore']

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

from xicam.plugins import manager as pluginmanager


# import qdarkstyle

class ipythonconsole(RichJupyterWidget):
    def __init__(self):
        super(ipythonconsole, self).__init__()
        ipythonplugin = pluginmanager.getPluginByName('IPython', 'GUIPlugin').plugin_object

        self.kernel_manager = ipythonplugin.kernel_manager
        self.kernel_client = ipythonplugin.kernel_client

        # self.style_sheet = (qdarkstyle.load_stylesheet())
        self.syntax_style = u'monokai'
        self.set_default_style(colors='Linux')

    def stop(self):
        self.kernel_client.stop_channels()
        self.kernel_manager.shutdown_kernel()

    def push(self, d):
        self.kernel.shell.push(d)
