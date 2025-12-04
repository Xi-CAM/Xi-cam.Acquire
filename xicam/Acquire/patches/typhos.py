from qtpy.QtWidgets import QVBoxLayout
from qtpy import QtCore

def removeItem(self, item):
    if item is None:
        return
    QVBoxLayout.removeItem(self, item)
QVBoxLayout.removeItem = removeItem

# QtCore.Q_ENUMS = lambda _: None
QtCore.Q_ENUMS = QtCore.QEnum
