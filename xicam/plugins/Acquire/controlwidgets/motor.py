from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.uic import loadUi
import pyqtgraph as pg
from functools import partial
import os

from . import simplewidgets


class MotorControl(QWidget):
    sigTargetChanged = Signal()
    sigStatusChanged = Signal(int)

    def __init__(self, deviceitem):
        '''
        Parameters
        ----------
        motordevice :   Motor

        '''
        super(MotorControl, self).__init__()
        loadUi(os.path.join(os.path.dirname(__file__), 'motor.ui'), self)
        self.motordevice = deviceitem.device
        self.joylayout.addWidget(pg.JoystickButton())

        self.targetSpinBox = simplewidgets.placeHolderSpinBox(self.targetGo)

        self._updateRange()

        self._setTarget(self.motordevice.setpoint.value)

        self.targetHSlider.valueChanged.connect(self._setTarget)
        self.targetVSlider.valueChanged.connect(self._setTarget)
        self.targetDial.valueChanged.connect(self._setTarget)
        self.targetLineEditLayout.insertWidget(0, self.targetSpinBox)
        # self.targetSpinBox.returnPressed.connect(lambda: self._setTarget(self.targetSpinBox.text()))
        self.targetGo.clicked.connect(lambda: self._setTarget(self.targetSpinBox.text()))
        self.stopButton.clicked.connect(self.stop)

        self.motordevice.readback.subscribe(self._setCurrentValue)
        # motordevice.motor.add_callback('DMOV',partial(guiinvoker.invoke_in_main_thread,self._updateStatus))

        self.sigStatusChanged.connect(self._updateStatus)

        self._setCurrentValue(self.motordevice.readback.get())

        self.targetHSlider.update()
        self.targetVSlider.update()

    def _setTarget(self, value):
        value = float(value)
        self.motordevice.set(value)
        self.targetHValue.setNum(value)
        self.targetVValue.setNum(value)
        self.targetDialValue.setNum(value)
        self.targetHSlider.setValue(value)
        self.targetVSlider.setValue(value)
        self.targetDial.setValue(value)
        self.targetSpinBox.setValue(value)

    def _updateRange(self):
        min = 0  # self.motordevice.setpoint.low_limit # can't set min/max limits on simulated devices?
        max = 100  # self.motordevice.setpoint.high_limit
        self.targetHSlider.setRange(min, max)
        self.targetVSlider.setRange(min, max)
        self.targetDial.setRange(min, max)
        self.currentHSlider.setRange(min, max)
        self.currentVSlider.setRange(min, max)
        self.currentDial.setRange(min, max)

        self.targetHMax.setText(str(max))
        self.targetVMax.setText(str(max))
        self.targetHMin.setText(str(min))
        self.targetVMin.setText(str(min))
        self.currentHMax.setText(str(max))
        self.currentVMax.setText(str(max))
        self.currentHMin.setText(str(min))
        self.currentVMin.setText(str(min))

    def _setCurrentValue(self, value=None, obj=None, **kwargs):
        if obj: value = obj.get()
        self.currentHSlider.setValue(value)
        self.currentVSlider.setValue(value)
        self.currentDial.setValue(value)
        self.currentLineEdit.setText(str(value))

        self.currentHValue.setNum(value)
        self.currentVValue.setNum(value)
        self.currentDialValue.setNum(value)

    def _updateStatus(self, value, **kwargs):
        self.progressBar.setRange(0, value)
        self.progressBar.setValue(value)

        if value == 0:
            status = 'Moving to position...'
        elif value == 1:
            status = 'Ready...'
        else:
            status = 'Error: Unknown status!'

        self.statusLabel.setText(status)

    def stop(self):
        self._setTarget(self.motordevice.getValue())
        self.motordevice.stop()
