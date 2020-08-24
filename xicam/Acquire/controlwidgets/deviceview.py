from qtpy.QtWidgets import *
from qtpy.QtCore import *

from xicam.plugins import manager as pluginmanager


class DeviceView:

    def __init__(self):
        super(DeviceView, self).__init__()

        happi_settings_plugin = pluginmanager.get_plugin_by_name('happi_devices',
                                                                 'SettingsPlugin')
        self.view = happi_settings_plugin.devices_view
        self.model = happi_settings_plugin.devices_model

    # FIXME: device discovery is not officially an element of EPICS's design; early work will add devices explicitly
    # @threads.method
    # def refresh(self):
    #     self._model.clear()
    #
    #
    #
    #     # Find devices
    #     motors = ophyd.EpicsSignalRO('beamline:motors:devices', name='motors').value
    #     ais = ophyd.EpicsSignalRO('beamline:ais:devices', name='ais').value
    #     dios = ophyd.EpicsSignalRO('beamline:dios:devices', name='dios').value
    #     instruments = ophyd.EpicsSignalRO('beamline:instruments:devices', name='instruments').value
    #
    #     for pvname in motors:
    #         try:
    #             self._model.appendRow(DeviceItem(pvname, alsophyd.Motor('beamline:motors:' + pvname, name=pvname)))
    #         except BadPVName:
    #             msg.logMessage(f'PV named "{pvname}" is invalid.', msg.WARNING)

    # def selectionChanged(self, *args, **kwargs):
    #     indexes = self.selectedIndexes()
    #     if indexes and indexes[0].isValid():
    #         # from qtpy.QtCore import pyqtRemoveInputHook
    #         # pyqtRemoveInputHook()
    #         # import pdb; pdb.set_trace()
    #         item = self._model.itemFromIndex(indexes[0])
    #         from xicam.Acquire.controllers.areadetector import AreaDetectorController
    #         controllerclass = AreaDetectorController
    #         widget = controllerclass(item.data())
    #         self.sigShowControl.emit(widget)
