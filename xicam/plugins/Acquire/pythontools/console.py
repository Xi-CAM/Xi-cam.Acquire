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
        plugin_obj = pluginmanager.getPluginByName('IPython', 'GUIPlugin')
        ipp = plugin_obj.plugin_object
        if callable(ipp):
            ipp = plugin_obj.plugin_object = ipp()

        self.kernel_manager = ipp.kernel_manager
        self.kernel_client = ipp.kernel_client

        # self.style_sheet = (qdarkstyle.load_stylesheet())
        self.syntax_style = u'monokai'
        self.set_default_style(colors='Linux')

    def stop(self):
        self.kernel_client.stop_channels()
        self.kernel_manager.shutdown_kernel()

    def push(self, d):
        self.kernel.shell.push(d)
