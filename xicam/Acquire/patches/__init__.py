import sys
import struct
from pyqtgraph.parametertree import registerParameterType
from pyqtgraph.parametertree.parameterTypes import ListParameter
from qtpy.QtWidgets import QApplication
from qtpy import QtWidgets, QtCore, QtNetwork, QtGui
from pyqode import qt
from happi import from_container
from xicam.plugins import manager as plugin_manager

Qt_packages = {'QtWidgets': QtWidgets,
               'QtCore': QtCore,
               'QtNetwork': QtNetwork,
               'QtGui': QtGui}

whitelist = ['qApp', 'Signal']

for subpackage_name, subpackage in Qt_packages.items():
    setattr(qt, subpackage_name, subpackage)
    sys.modules[f"pyqode.qt.{subpackage_name}"] = subpackage

import builtins

if getattr(builtins, 'qApp', None):
    QtWidgets.qApp = qApp  # qApp is inserted in builtins by PySide2

from pyqode.core.api.client import JsonTcpClient, comm  # Must be a late import


def _read_header(self):
    comm('reading header')
    self._header_buf += self.read(4)
    if len(self._header_buf) == 4:
        self._header_complete = True
        try:
            if hasattr(self._header_buf, 'data'):
                raise TypeError  # The following line unforgivingly causes access violation on PySide2, skip to doing it right
            header = struct.unpack('=I', self._header_buf)
        except TypeError:
            # pyside
            header = struct.unpack('=I', self._header_buf.data())
        self._to_read = header[0]
        self._header_buf = bytes()
        comm('header content: %d', self._to_read)


JsonTcpClient._read_header = _read_header


#     for member in dir(subpackage):
#         if member.startswith('Q') or member in whitelist:
#             sys.modules[f"pyqode.qt.{subpackage_name}.{member}"] = getattr(subpackage, member)
#
# sys.modules['pyqode.qt.QtWidgets.qApp'] = qApp or QApplication.instance()  # qApp is inserted in builtins by PySide2


# Add a Device parametertype
class DeviceParameter(ListParameter):
    def __init__(self, search: dict = None, **opts):
        ## Parameter uses 'limits' option to define the set of allowed values
        if opts.get('values', None) is None:
            devices = [from_container(container.device)
                       for container in
                       plugin_manager.get_plugin_by_name('HappiSettingsPlugin', 'SettingsPlugin').search(
                           **(search or {}))]
            opts['values'] = devices

        super(DeviceParameter, self).__init__(**opts)


registerParameterType('Device', DeviceParameter, override=True)
