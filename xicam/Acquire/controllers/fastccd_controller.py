from pydm.widgets import PyDMPushButton, PyDMLabel
from qtpy.QtWidgets import QGroupBox, QVBoxLayout
from .areadetector import AreaDetectorController
from xicam.plugins import manager as plugin_manager
from xicam.SAXS.ontology import NXsas


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

        # Find coupled devices and add them so they'll be used with RE
        self.coupled_devices += plugin_manager.get_plugin_by_name("happi_devices", "SettingsPlugin").search(
            prefix=device.prefix)

        self.metadata["projections"] = [{'name': 'NXsas',
                    'version': '0.1.0',
                    'projection':
                        {NXsas.DATA_PROJECTION_KEY: {'type': 'linked',
                                               'stream': 'primary',
                                               'location': 'event',
                                               'field': f"{device.name}_image"}},
                    'configuration': {}
                    }]
