from pydm.widgets import PyDMPushButton, PyDMLabel
from qtpy.QtWidgets import QGroupBox, QVBoxLayout
from .areadetector import AreaDetectorController


class FastCCDController(AreaDetectorController):
    def __init__(self, device):
        super(FastCCDController, self).__init__(device)

        camera_layout = QVBoxLayout()
        camera_panel = QGroupBox('Camera State')
        camera_panel.setLayout(camera_layout)

        camera_layout.addWidget(PyDMLabel(init_channel=f'ca://{device.cam.state.pvname}'))

        camera_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.cam.initialize.setpoint_pvname}',
                           label='Initialize'))
        camera_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.cam.shutdown.setpoint_pvname}', label='Shutdown'))

        dg_layout = QVBoxLayout()
        dg_panel = QGroupBox('Delay Gen State')
        dg_panel.setLayout(dg_layout)

        dg_layout.addWidget(PyDMLabel(init_channel=f'ca://{device.dg1.state.pvname}'))

        dg_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.dg1.initialize.setpoint_pvname}',
                           label='Initialize'))
        dg_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.dg1.reset.setpoint_pvname}', label='Reset'))

        self.hlayout.addWidget(camera_panel)
        self.hlayout.addWidget(dg_panel)
