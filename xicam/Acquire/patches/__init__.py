import sys
import struct

from happi import from_container
from pyqtgraph.parametertree import parameterTypes, registerParameterType
from qtpy.QtWidgets import QApplication
from qtpy import QtWidgets, QtCore, QtNetwork, QtGui
from pyqode import qt

from xicam.core import msg

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


class DeviceParameter(parameterTypes.ListParameter):
    def __init__(self, device_filter=None, **opts):
        if not opts.get('limits', None):
            from xicam.plugins import manager as plugin_manager
            happi_devices = plugin_manager.get_plugin_by_name('happi_devices', 'SettingsPlugin')
            opts['limits'] = dict()
            for container in happi_devices.search(**(device_filter or {})):
                try:
                    opts['limits'][container.device.name] = from_container(container.device)
                except Exception as ex:
                     msg.logError(ex)

        super(DeviceParameter, self).__init__(**opts)


registerParameterType("device", DeviceParameter)
