from qtpy.QtWidgets import *
from qtpy.QtGui import *
from qtpy.QtCore import *

from alsdac import ophyd as alsophyd
import ophyd
from ophyd.utils.epics_pvs import BadPVName
from xicam.core import msg
from xicam.gui import threads

from .motor import MotorControl


class DeviceList(QListView):
    sigShowControl = Signal(QWidget)

    def __init__(self):
        super(DeviceList, self).__init__()

        self._model = QStandardItemModel()

        self.refresh()

        self.setModel(self._model)

    @threads.method
    def refresh(self):
        self._model.clear()

        # Find devices
        motors = ophyd.EpicsSignalRO('beamline:motors:devices', name='motors').value
        ais = ophyd.EpicsSignalRO('beamline:ais:devices', name='ais').value
        dios = ophyd.EpicsSignalRO('beamline:dios:devices', name='dios').value
        instruments = ophyd.EpicsSignalRO('beamline:instruments:devices', name='instruments').value

        for pvname in motors:
            try:
                self._model.appendRow(DeviceItem(pvname, alsophyd.Motor('beamline:motors:' + pvname, name=pvname)))
            except BadPVName:
                msg.logMessage(f'PV named "{pvname}" is invalid.', msg.WARNING)

    def selectionChanged(self, *args, **kwargs):
        indexes = self.selectedIndexes()
        if indexes and indexes[0].isValid():
            item = self._model.itemFromIndex(indexes[0])
            self.sigShowControl.emit(item.widget)

    # def refreshDevices(self):
    #     for i in range(self._model.rowCount()):
    #         device = self._model.item(i).device
    #         if isinstance(device, sim.Syn2DGauss): continue
    #         device.readback._run_subs(sub_type='value')


class DeviceItem(QStandardItem):
    def __init__(self, title, device):
        super(DeviceItem, self).__init__(title)
        self.device = device
        self._widget = None

    @property
    def widget(self):
        from typhon import DeviceDisplay
        from pydm import application
        import typhon.plugins
        if self._widget is None:
            self._widget = DeviceDisplay(self.device)
        application.PyDMApplication.establish_widget_connections(QApplication.instance(), self._widget)
        return self._widget
