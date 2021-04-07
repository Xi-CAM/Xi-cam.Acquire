from PyQt5 import QtWidgets, uic, QtGui
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
Form, Base = uic.loadUiType(os.path.join(current_dir, "../ui/scan_display.ui"))


