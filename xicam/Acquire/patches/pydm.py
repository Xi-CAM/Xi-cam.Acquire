from unittest import mock

import pydm
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QStyleOption, QStyle


# A patch to fix drawing ellipses with certain newer Qt python bindings
def paintEvent(self, event):
    """
    Paint events are sent to widgets that need to update themselves,
    for instance when part of a widget is exposed because a covering
    widget was moved.

    Parameters
    ----------
    event : QPaintEvent
    """
    self._painter.begin(self)
    opt = QStyleOption()
    opt.initFrom(self)
    self.style().drawPrimitive(QStyle.PE_Widget, opt, self._painter, self)
    self._painter.setRenderHint(QPainter.Antialiasing)
    self._painter.setBrush(self._brush)
    self._painter.setPen(self._pen)
    if self.circle:
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        r = min(w, h) / 2.0 - 2.0 * max(self._pen.widthF(), 1.0)
        self._painter.drawEllipse(QPoint(int(w / 2.0), int(h / 2.0)), int(r), int(r))
    else:
        self._painter.drawRect(self.rect())
    self._painter.end()

pydm.widgets.byte.PyDMBitIndicator.paintEvent = paintEvent


class IntSignal():
    def __init__(self, qt_signal):
        self.qt_signal = qt_signal

    def __getitem__(self, item):
        if item != int:
            raise NotImplementedError
        return self

    def emit(self, value):
        self.qt_signal.emit(int(value))

_send_value = pydm.widgets.line_edit.PyDMLineEdit.send_value

def send_value(self):
    qt_signal = self.send_value_signal
    self.send_value_signal = IntSignal(qt_signal)
    ret = _send_value(self)
    self.send_value_signal = qt_signal
    return ret

pydm.widgets.line_edit.PyDMLineEdit.send_value = send_value
