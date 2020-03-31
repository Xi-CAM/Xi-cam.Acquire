from xicam.plugins import ControllerPlugin
from typhos import TyphosDeviceDisplay


class TyphosMotorController(TyphosDeviceDisplay, ControllerPlugin):
    def __new__(cls, device, *args, **kwargs):
        splay = TyphosDeviceDisplay.from_device(device.device_obj)
        return splay

    def __init__(self, pvname):
        super(TyphosMotorController, self).__init__(pvname)

# from pydm import application
# import typhon.plugins
# if self._widget is None:
#     self._widget = DeviceDisplay(self.device)
# application.PyDMApplication.establish_widget_connections(QApplication.instance(), self._widget)
# return self._widget
