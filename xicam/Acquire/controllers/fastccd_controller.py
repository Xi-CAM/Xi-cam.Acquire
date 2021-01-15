import numpy as np

from databroker import Broker
from databroker.core import BlueskyRun
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

        # TODO: pull from settingsplugin
        self.db = Broker.named('local').v2

    # def preprocess(self, image):
    #
    #     try:
    #         dark = self.get_dark(self.db[-1])  # TODO: Look back a few runs for the dark frame
    #         return image-dark
    #     except AttributeError:
    #         return image

    def get_dark(self, run_catalog: BlueskyRun):
        return np.asarray(run_catalog.dark.to_dask()['fastccd_image']).squeeze()

    def setPassive(self, passive: bool):
        if self.RE.isIdle:
            ...
            # self.device.
