from xicam.plugins import ControllerPlugin
from typhos import TyphosDeviceDisplay
import typhos


class TyphosMotorController(TyphosDeviceDisplay, ControllerPlugin):
    def __new__(cls, device, *args, **kwargs):
        splay = TyphosDeviceDisplay.from_device(device.device_obj)
        return splay

    def __init__(self, pvname):
        super(TyphosMotorController, self).__init__(pvname)
