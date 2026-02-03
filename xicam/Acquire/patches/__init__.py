import enum

import sys
import struct


from happi import from_container
from pyqtgraph.parametertree import parameterTypes, registerParameterType
from pyqtgraph.parametertree.Parameter import PARAM_TYPES
from qtpy.QtWidgets import QApplication
from qtpy import QtWidgets, QtCore, QtNetwork, QtGui
from pyqode import qt

from xicam.core import msg

from . import pydm
from . import typhos

Qt_packages = {'QtWidgets': QtWidgets,
               'QtCore': QtCore,
               # 'QtNetwork': QtNetwork,
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

def sizeHint(self):
    """
    Returns the panel size hint. (fixed with of 16px)
    """
    metrics = QtGui.QFontMetricsF(self.editor.font())
    size_hint = QtCore.QSize(int(metrics.height()), int(metrics.height()))
    if size_hint.width() > 16:
        size_hint.setWidth(16)
    return size_hint

import pyqode.core.panels
pyqode.core.panels.checker.CheckerPanel.sizeHint = sizeHint


def _paint_margin(self, event):
    """ Paints the right margin after editor paint event. """
    font = QtGui.QFont(self.editor.font_name, self.editor.font_size +
                       self.editor.zoom_level)
    metrics = QtGui.QFontMetricsF(font)
    pos = self._margin_pos
    offset = self.editor.contentOffset().x() + \
             self.editor.document().documentMargin()
    x80 = round(metrics.width(' ') * pos) + offset
    painter = QtGui.QPainter(self.editor.viewport())
    painter.setPen(self._pen)
    painter.drawLine(int(x80), 0, int(x80), 2 ** 16)

import pyqode.core.modes
pyqode.core.modes.right_margin.RightMarginMode._paint_margin = _paint_margin


def sizeHint(self):
    """ Returns the widget size hint (based on the editor font size) """
    fm = QtGui.QFontMetricsF(self.editor.font())
    size_hint = QtCore.QSize(int(fm.height()), int(fm.height()))
    if size_hint.width() > 16:
        size_hint.setWidth(16)
    return size_hint

pyqode.core.panels.folding.FoldingPanel.sizeHint = sizeHint

class DeviceParameter(parameterTypes.ListParameter):
    def __init__(self, device_filter=None, **opts):
        if not opts.get('limits', None):
            from xicam.plugins import manager as plugin_manager
            happi_devices = plugin_manager.get_plugin_by_name('happi_devices', 'SettingsPlugin')
            opts['limits'] = dict()
            for container in happi_devices.search(**(device_filter or {})):
                try:
                    opts['limits'][container.item.name] = from_container(container.item)
                except Exception as ex:
                     msg.logError(ex)

        super(DeviceParameter, self).__init__(**opts)


if 'device' not in PARAM_TYPES:
    registerParameterType("device", DeviceParameter)


def promote_enums(module):
    """
    Search enums in the given module and allow unscoped access.

    Taken from:
    https://github.com/pyqtgraph/pyqtgraph/blob/pyqtgraph-0.12.1/pyqtgraph/Qt.py#L331-L377
    and adapted to also copy enum values aliased under different names.

    """
    class_names = [name for name in dir(module) if name.startswith("Q")]
    for class_name in class_names:
        klass = getattr(module, class_name)
        attrib_names = [name for name in dir(klass) if name[0].isupper()]
        for attrib_name in attrib_names:
            attrib = getattr(klass, attrib_name)
            if not isinstance(attrib, enum.EnumMeta):
                continue
            for name, value in attrib.__members__.items():
                setattr(klass, name, value)

promote_enums(QtCore)
promote_enums(QtGui)
promote_enums(QtWidgets)