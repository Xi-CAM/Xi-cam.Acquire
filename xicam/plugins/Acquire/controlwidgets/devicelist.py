from qtpy.QtWidgets import *
from qtpy.QtGui import *
from qtpy.QtCore import *

import ophyd
from ophyd import sim

from .motor import MotorControl


class DeviceList(QListView):
    sigShowControl = Signal(QWidget)

    def __init__(self):
        super(DeviceList, self).__init__()

        self._model = QStandardItemModel()

        # Setup simulated motors
        sim1 = sim.SynAxis(name='motor1', delay=.1)
        sim2 = sim.SynAxis(name='motor2', delay=.1)
        sim3 = sim.SynAxis(name='motor3', delay=.1)

        # self._model.appendRow(DeviceItem('"Gaussian" Detector', sim.det4))
        self._model.appendRow(DeviceItem('X motor', sim1))
        self._model.appendRow(DeviceItem('Y motor', sim2))
        self._model.appendRow(DeviceItem('Z motor', sim3))

        # Watch each item
        # self.refreshtimer = QTimer()
        # self.refreshtimer.setInterval(.1)
        # self.refreshtimer.timeout.connect(self.refreshDevices)
        # self.refreshtimer.start()

        self.setModel(self._model)

    def selectionChanged(self, *args, **kwargs):
        indexes = self.selectedIndexes()
        if indexes and indexes[0].isValid():
            item = self._model.itemFromIndex(indexes[0])
            self.sigShowControl.emit(item.widget)

    def refreshDevices(self):
        for i in range(self._model.rowCount()):
            device = self._model.item(i).device
            if isinstance(device, sim.Syn2DGauss): continue
            device.readback._run_subs(sub_type='value')


class DeviceItem(QStandardItem):
    def __init__(self, title, device):
        super(DeviceItem, self).__init__(title)
        self.device = device
        self._widget = None

    @property
    def widget(self):
        from typhon import DeviceDisplay
        import typhon.plugins
        if self._widget is None:
            self._widget = DeviceDisplay(self.device)
        return self._widget
