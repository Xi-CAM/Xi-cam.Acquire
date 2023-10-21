import time

from ophyd import set_and_wait
from qtpy.QtCore import Qt, QTimer
from pydm.widgets.display_format import DisplayFormat
from qtpy.QtWidgets import QHBoxLayout, QGroupBox, QVBoxLayout, QFormLayout, QComboBox, QApplication
from pydm.widgets import PyDMLineEdit, PyDMLabel, PyDMPushButton, PyDMEnumComboBox

from .areadetector import LabViewCoupledController
from bluesky import plan_stubs as bps

from xicam.core.msg import logMessage


class LiveModeCompatibleLineEdit(PyDMLineEdit):
    def __init__(self, device, *args, **kwargs):
        self.device = device
        super(LiveModeCompatibleLineEdit, self).__init__(*args, **kwargs)

    def send_value(self):
        #temporarily stop acquisition before changing value
        set_and_wait(self.device.cam.acquire, 0)
        time.sleep(.5)
        super(LiveModeCompatibleLineEdit, self).send_value()
        QTimer.singleShot(500, self._resume_acquire)

    def _resume_acquire(self):
        set_and_wait(self.device.cam.acquire, 1)


class PIMTE3Controller(LabViewCoupledController):
    view_kwargs = {'allow_active': False}

    def __init__(self, device, *args, **kwargs):
        super(PIMTE3Controller, self).__init__(device, *args, **kwargs)

        self.idle_mode = 'Inactive'

        self.num_exposures_line_edit = LiveModeCompatibleLineEdit(device=device, init_channel=f'ca://{device.cam.num_exposures.setpoint_pvname}')
        self.num_images_line_edit = LiveModeCompatibleLineEdit(device=device, init_channel=f'ca://{device.cam.num_images.setpoint_pvname}')
        self.readout_time_line_edit = PyDMLabel(init_channel=f'ca://{device.cam.readout_time.pvname}')
        self.config_layout.addRow('Acquire Time (ms)', PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_time.setpoint_pvname}'))
        self.config_layout.addRow('Number of Accumulations', self.num_exposures_line_edit)
        self.config_layout.addRow('Number of Images', self.num_images_line_edit)
        self.config_layout.addRow('Readout Time (ms)', self.readout_time_line_edit)


        shutter_layout = QFormLayout()
        shutter_panel = QGroupBox('Shutter')
        shutter_panel.setLayout(shutter_layout)
        shutter_layout.addRow('Shutter Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.shutter_mode.setpoint_pvname}'))
        shutter_layout.addRow('Detector Status', PyDMLabel(init_channel=f'ca://{device.cam.detector_state.pvname}'))
        self.idle_mode_selector = QComboBox()
        self.idle_mode_selector.addItems(['Inactive', 'TV Mode'])
        if self.device.cam.image_mode.get() == 2:
            self.idle_mode_selector.setCurrentText('TV Mode')
        shutter_layout.addRow('Idle Mode', self.idle_mode_selector)
        self.idle_mode_selector.currentTextChanged.connect(self.set_idle_mode)

        cooler_layout = QFormLayout()
        cooler_panel = QGroupBox('Temperature')
        cooler_panel.setLayout(cooler_layout)
        # cooler_layout.addRow('State', PyDMEnumComboBox(init_channel=f'ca://{device.cam.andor_cooler.setpoint_pvname}'))
        cooler_layout.addRow('Sensor Temperature (C)', PyDMLabel(init_channel=f'ca://{device.cam.temperature_actual.pvname}'))
        cooler_layout.addRow('Temperature Setpoint (C)', PyDMLineEdit(init_channel=f'ca://{device.cam.temperature.setpoint_pvname}'))
        # temp_status = PyDMLabel(init_channel=f'ca://{device.cam.andor_temp_status.pvname}')
        # temp_status.displayFormat = DisplayFormat.String
        # cooler_layout.addWidget(temp_status)

        self.hlayout.addWidget(cooler_panel)
        self.hlayout.addWidget(shutter_panel)

        self.RE.sigStart.connect(self.on_plan_start, Qt.BlockingQueuedConnection)
        self.RE.sigFinish.connect(self.on_plan_finish, Qt.BlockingQueuedConnection)

    def _plan(self):
        yield from bps.open_run()

        # stash numcapture and shutter_enabled and num_exposures
        # num_capture = yield from bps.rd(self.device.hdf5.num_capture)
        shutter_state = yield from bps.rd(self.device.cam.shutter_mode)
        num_images = yield from bps.rd(self.device.cam.num_images)

        try:
            # set to 1 temporarily
            # self.device.hdf5.num_capture.put(10)

            # Always do 10 exposures for dark
            # self.device.cam.num_exposures.put(dark_exposures)
            yield from bps.mv(self.device.cam.num_images, 10)

            # Restage to ensure that dark frames goes into a separate file.
            yield from bps.stage(self.device)
            yield from bps.mv(self.device.cam.shutter_mode, 2)
            # The `group` parameter passed to trigger MUST start with
            # bluesky-darkframes-trigger.
            yield from bps.trigger_and_read([self.device], name='dark')
            # Restage.
            yield from bps.unstage(self.device)
            # restore numcapture and shutter_enabled and num_exposures
        finally:
            # yield from bps.mv(self.device.hdf5.num_capture, num_capture)
            yield from bps.mv(self.device.cam.shutter_mode, shutter_state)
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

    def on_plan_start(self):
        if self.idle_mode_selector.currentText() == 'TV Mode':
            self.stop_tv()

    def on_plan_finish(self):
        if self.idle_mode_selector.currentText() == 'TV Mode':
            self.start_tv()

    def start_tv(self):
        logMessage('starting tv mode')
        self.device.cam.image_mode.put(2)
        self.device.cam.acquire.put(1)
        self.num_images_line_edit.setReadOnly(False)
        self.num_exposures_line_edit.setReadOnly(False)

    def stop_tv(self):
        logMessage('stopping tv mode')
        self.device.cam.acquire.put(0)
        self.device.cam.image_mode.put(1)
        self.num_images_line_edit.setReadOnly(True)
        self.num_exposures_line_edit.setReadOnly(True)

    def set_idle_mode(self, mode):
        if self.RE.isIdle:
            if mode == 'TV Mode':
                self.idle_mode = mode
                self.start_tv()
            else:
                self.stop_tv()
        self.idle_mode = mode

