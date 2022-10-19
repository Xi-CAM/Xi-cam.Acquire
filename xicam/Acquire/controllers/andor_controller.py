from pydm.widgets import PyDMLineEdit

from .areadetector import LabViewCoupledController


class AndorController(LabViewCoupledController):
    def __init__(self, device, *args, **kwargs):
        super(AndorController, self).__init__(device, *args, **kwargs)
        self.config_layout.removeRow(1)  # Remove period

        self.config_layout.addRow('Number of Images', PyDMLineEdit(init_channel=f'ca://{device.cam.num_images.setpoint_pvname}'))
