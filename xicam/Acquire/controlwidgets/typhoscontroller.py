from xicam.plugins import ControllerPlugin
from typhos import TyphosDeviceDisplay


class TyphosController(TyphosDeviceDisplay, ControllerPlugin):
    def __new__(cls, device, *args, **kwargs):
        splay = TyphosDeviceDisplay.from_device(device.device_obj)
        return splay

    def __init__(self, pvname):
        super(TyphosController, self).__init__(pvname)
