import numpy as np

from databroker import Broker
from databroker.core import BlueskyRun
from happi import from_container
from pydm.widgets import PyDMPushButton, PyDMLabel
from qtpy.QtWidgets import QGroupBox, QVBoxLayout
from .areadetector import AreaDetectorController
from xicam.plugins import manager as plugin_manager


# Pulled from NDPluginFastCCD.h:11
FCCD_MASK = 0x1FFF


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
        self.passive.deleteLater()  # active mode is useless for fastccd at COSMIC-Scattering

        # TODO: pull from settingsplugin
        self.db = Broker.named('local').v2

        # Find coupled devices and add them so they'll be used with RE
        self.coupled_devices += map(lambda search_result: from_container(search_result.device),
                                    plugin_manager.get_plugin_by_name("happi_devices", "SettingsPlugin").search(
                                        prefix=device.prefix))

    # def preprocess(self, image):
    #
    #     try:
    #         dark = self.get_dark(self.db[-1])  # TODO: Look back a few runs for the dark frame
    #         return image-dark
    #     except AttributeError:
    #         return image

    def _bitmask(self, array):
        return array.astype(int) & FCCD_MASK

    def get_dark(self, run_catalog: BlueskyRun):
        darks = np.asarray(run_catalog.dark.to_dask()['fastccd_image']).squeeze()
        return self._bitmask(darks)

    def setPassive(self, passive: bool):
        if self.RE.isIdle:
            ...
            # self.device.

    def preprocess(self, image):
        return self._bitmask(image)  # 0x1FFF