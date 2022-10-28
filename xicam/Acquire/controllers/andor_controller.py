from pydm.widgets.display_format import DisplayFormat
from qtpy.QtWidgets import QHBoxLayout, QGroupBox, QVBoxLayout, QFormLayout
from pydm.widgets import PyDMLineEdit, PyDMLabel, PyDMPushButton, PyDMEnumComboBox

from .areadetector import LabViewCoupledController
from bluesky import plan_stubs as bps


class AndorController(LabViewCoupledController):
    def __init__(self, device, *args, **kwargs):
        super(AndorController, self).__init__(device, *args, **kwargs)
        self.config_layout.removeRow(1)  # Remove period

        self.config_layout.addRow('Number of Images', PyDMLineEdit(init_channel=f'ca://{device.cam.num_images.setpoint_pvname}'))

        shutter_layout = QFormLayout()
        shutter_panel = QGroupBox('Shutter')
        shutter_panel.setLayout(shutter_layout)
        shutter_layout.addRow('Shutter Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.andor_shutter_mode.setpoint_pvname}'))

        cooler_layout = QFormLayout()
        cooler_panel = QGroupBox('Cooler')
        cooler_panel.setLayout(cooler_layout)
        cooler_layout.addRow('State', PyDMEnumComboBox(init_channel=f'ca://{device.cam.andor_cooler.setpoint_pvname}'))
        cooler_layout.addRow('Setpoint', PyDMLineEdit(init_channel=f'ca://{device.cam.temperature.setpoint_pvname}'))
        cooler_layout.addRow('Temperature', PyDMLabel(init_channel=f'ca://{device.cam.temperature_actual.pvname}'))
        temp_status = PyDMLabel(init_channel=f'ca://{device.cam.andor_temp_status.pvname}')
        temp_status.displayFormat = DisplayFormat.String
        cooler_layout.addWidget(temp_status)

        self.hlayout.addWidget(shutter_panel)
        self.hlayout.addWidget(cooler_panel)


    def _plan(self):
        yield from bps.open_run()

        # stash numcapture and shutter_enabled and num_exposures
        # num_capture = yield from bps.rd(self.device.hdf5.num_capture)
        shutter_state = yield from bps.rd(self.device.cam.andor_shutter_mode)
        num_images = yield from bps.rd(self.device.cam.num_images)

        try:
            # set to 1 temporarily
            # self.device.hdf5.num_capture.put(10)

            # Always do 10 exposures for dark
            # self.device.cam.num_exposures.put(dark_exposures)
            yield from bps.mv(self.device.cam.num_images, 10)

            # Restage to ensure that dark frames goes into a separate file.
            yield from bps.stage(self.device)
            yield from bps.mv(self.device.cam.andor_shutter_mode, 2)
            # The `group` parameter passed to trigger MUST start with
            # bluesky-darkframes-trigger.
            yield from bps.trigger_and_read([self.device], name='dark')
            # Restage.
            yield from bps.unstage(self.device)
            # restore numcapture and shutter_enabled and num_exposures
        finally:
            # yield from bps.mv(self.device.hdf5.num_capture, num_capture)
            yield from bps.mv(self.device.cam.andor_shutter_mode, shutter_state)
            yield from bps.mv(self.device.cam.num_images, num_images)

        try:
            # Dark frames finished, moving on to data
            yield from bps.stage(self.device)
            status = yield from bps.trigger(self.device, group='primary-trigger')
            while not status.done:
                yield from bps.trigger_and_read(set(self.coupled_devices).difference({self.device}), name='labview')
                yield from bps.sleep(1)
            yield from bps.create('primary')
            yield from bps.read(self.device)
            yield from bps.save()
        finally:
            yield from bps.unstage(self.device)

    def acquire(self):
        self.RE(self._plan(), **self.metadata)