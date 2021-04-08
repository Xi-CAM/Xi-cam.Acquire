import numpy as np
from bluesky.plans import count
import bluesky.plan_stubs as bps
from databroker import Broker
from databroker.core import BlueskyRun
from happi import from_container
from ophyd import Device
from pydm.widgets import PyDMPushButton, PyDMLabel
from qtpy.QtWidgets import QGroupBox, QVBoxLayout
from .areadetector import AreaDetectorController
from xicam.plugins import manager as plugin_manager
from xicam.SAXS.ontology import NXsas
from xicam.core.msg import logError


# Pulled from NDPluginFastCCD.h:11
FCCD_MASK = 0x1FFF


class FastCCDController(AreaDetectorController):
    def __init__(self, device: Device):
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

        happi_settings = plugin_manager.get_plugin_by_name("happi_devices", "SettingsPlugin")

        # Find coupled devices and add them so they'll be used with RE
        def from_device_container(container) -> Device:
            try:
                return from_container(container.device)
            except Exception as e:
                logError(e)
                return None


        self.async_poll_devices = list(map(from_device_container,
                                           happi_settings.search(source='labview')))
        self.async_poll_devices += map(from_device_container,
                                       happi_settings.search(
                                           prefix=device.prefix))

        # Remove errored from_container devices (Nones)
        self.async_poll_devices = list(filter(lambda device: device, self.async_poll_devices))

        self.async_poll_devices.remove(device)

        self.metadata["projections"] = [{'name': 'NXsas',
                                         'version': '0.1.0',
                                         'projection':
                                             {NXsas.DATA_PROJECTION_KEY: {'type': 'linked',
                                                                          'stream': 'primary',
                                                                          'location': 'event',
                                                                          'field': f"{device.name}_image"},
                                              NXsas.AZIMUTHAL_ANGLE_PROJECTION_KEY: {'type': 'linked',
                                                                                     'stream': 'labview',
                                                                                     'location': 'event',
                                                                                     'field': 'detector_rotate'},
                                              # TODO: source this from somewhere
                                              NXsas.ENERGY_PROJECTION_KEY: {'type': 'linked',
                                                                            'stream': 'labview',
                                                                            'location': 'event',
                                                                            'field': 'mono_energy'},
                                              NXsas.INCIDENCE_ANGLE_PROJECTION_KEY: {'type': 'linked',
                                                                                     'stream': 'labview',
                                                                                     'location': 'event',
                                                                                     'field': 'sample_rotate_steppertheta'},
                                              # TODO: CHECK IF THIS EXISTS
                                              # FIXME: Is this the right motor???
                                              NXsas.DETECTOR_TRANSLATION_X_PROJECTION_KEY: {'type': 'linked',
                                                                                            'stream': 'labview',
                                                                                            'location': 'event',
                                                                                            'field': 'det_translate'},
                                              },
                                         'configuration': {'detector_name': 'fastccd',
                                                           'sdd': 0.5,
                                                           'geometry_mode': 'transmission',
                                                           'poni1': 480,
                                                           'poni2': 1025
                                                           }
                                         }]

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
        return self._bitmask(image) - self.get_dark(Broker.named('local').v2[-1])

    def _plan(self):
        yield from bps.open_run()

        # stash numcapture
        num_capture = yield from bps.rd(self.device.hdf5.num_capture)

        # set to 1 temporarily
        self.device.hdf5.num_capture.put(1)

        # Restage to ensure that dark frames goes into a separate file.
        yield from bps.stage(self.device)
        yield from bps.mv(self.device.dg1.shutter_enabled, False)
        # The `group` parameter passed to trigger MUST start with
        # bluesky-darkframes-trigger.
        yield from bps.trigger_and_read([self.device], name='dark')
        yield from bps.mv(self.device.dg1.shutter_enabled, True)
        # Restage.
        yield from bps.unstage(self.device)
        # restore numcapture
        yield from bps.mv(self.device.hdf5.num_capture, num_capture)

        # Dark frames finished, moving on to data

        yield from bps.stage(self.device)
        status = yield from bps.trigger(self.device, group='primary-trigger')
        while not status.done:
            yield from bps.trigger_and_read(self.async_poll_devices, name='labview')
            yield from bps.sleep(1)
        yield from bps.create('primary')
        yield from bps.read(self.device)
        yield from bps.save()
        yield from bps.unstage(self.device)

    def acquire(self):
        self.RE(self._plan(), **self.metadata)
