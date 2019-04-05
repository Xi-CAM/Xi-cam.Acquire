class Device(object):
    def __init__(self, name, pvname, controller, device_cls):
        self.name = name
        self.pvname = pvname
        self.controller = controller
        self.device_cls = device_cls
        self._device_obj = None

    @property
    def device_obj(self):
        if not self._device_obj:
            self._device_obj = self.device_cls(prefix=self.pvname, name=self.name)
        return self._device_obj

    def __reduce__(self):
        return Device, (self.name, self.pvname, self.controller, self.device_cls)
