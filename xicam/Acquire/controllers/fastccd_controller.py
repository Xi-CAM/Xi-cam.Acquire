import numpy as np
from PyQt5.QtWidgets import QLabel
from bluesky.plans import count
import bluesky.plan_stubs as bps
from databroker import Broker
from databroker.core import BlueskyRun
from happi import from_container
from ophyd import Device
from pydm.widgets import PyDMPushButton, PyDMLabel, PyDMCheckbox
from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout
from .areadetector import AreaDetectorController
from xicam.plugins import manager as plugin_manager
from xicam.SAXS.ontology import NXsas
from xicam.core.msg import logError, notifyMessage, ERROR
from xicam.SAXS.operations.correction import correct


# Pulled from NDPluginFastCCD.h:11
FCCD_MASK = 0x1FFF
dark_exposures = 1


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
        auto_start = PyDMCheckbox(init_channel=f'ca://{device.cam.auto_start.setpoint_pvname}')
        auto_start.setText('Auto Start')
        camera_layout.addWidget(auto_start)

        dg_layout = QHBoxLayout()
        dg_panel = QGroupBox('Delay Gen State')
        dg_panel.setLayout(dg_layout)

        dg_state_layout = QVBoxLayout()
        dg_layout.addLayout(dg_state_layout)
        dg_state_layout.addWidget(PyDMLabel(init_channel=f'ca://{device.dg1.state.pvname}'))

        dg_state_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.dg1.initialize.setpoint_pvname}',
                           label='Initialize'))
        dg_state_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.dg1.reset.setpoint_pvname}', label='Reset'))

        dg_shutter_layout = QVBoxLayout()
        dg_layout.addLayout(dg_shutter_layout)
        dg_shutter_layout.addWidget(PyDMLabel(init_channel=f'ca://{device.dg1.shutter_enabled.pvname}'))
        dg_shutter_layout.addWidget(
            PyDMPushButton(pressValue=0, init_channel=f'ca://{device.dg1.shutter_enabled.setpoint_pvname}',
                           label='Enable Trigger')
        )
        dg_shutter_layout.addWidget(
            PyDMPushButton(pressValue=2, init_channel=f'ca://{device.dg1.shutter_enabled.setpoint_pvname}',
                           label='Keep Closed')
        )
        dg_shutter_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.dg1.shutter_enabled.setpoint_pvname}',
                           label='Keep Open')
        )

        self.hlayout.addWidget(camera_panel)
        self.hlayout.addWidget(dg_panel)
        self.passive.setVisible(False)  # active mode is useless for fastccd at COSMIC-Scattering

        # Subscribe to the error status PV so we can create notifications
        # (only relevant for cam init errors for now)
        self.device.cam.error_status.subscribe(self.report_error, 'value')

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

    def report_error(self, value, **_):
        text = bytes(value).decode()
        if text:
            title = "Camera Initialization Error"
            notifyMessage(text, title=title, level=ERROR)

    def _bitmask(self, array):
        return array.astype(int) & FCCD_MASK

    def get_dark(self, run_catalog: BlueskyRun):
        darks = np.asarray(run_catalog.dark.to_dask()['fastccd_image']).squeeze()
        if darks.ndim == 3:
            darks = np.mean(darks, axis=0)
        return darks

    def preprocess(self, image):
        if self.bg_correction.isChecked():
            try:
                flats = np.ones_like(image)
                darks = self.get_dark(Broker.named('local').v2[-1])
                image = correct(np.expand_dims(image, 0), flats, darks)[0]
            except Exception:
                pass
        else:
            image = image.astype(np.uint16) & 0x1FFF
        image = np.delete(image, slice(966, 1084), 1)
        return image

    def _plan(self):
        yield from bps.open_run()

        # stash numcapture and shutter_enabled and num_exposures
        num_capture = yield from bps.rd(self.device.hdf5.num_capture)
        shutter_enabled = yield from bps.rd(self.device.dg1.shutter_enabled)
        # num_exposures = yield from bps.rd(self.device.cam.num_exposures)

        try:
            # set to 1 temporarily
            self.device.hdf5.num_capture.put(10)

            # Always do 10 exposures for dark
            # self.device.cam.num_exposures.put(dark_exposures)

            # Restage to ensure that dark frames goes into a separate file.
            yield from bps.stage(self.device)
            yield from bps.mv(self.device.dg1.shutter_enabled, 2)
            # The `group` parameter passed to trigger MUST start with
            # bluesky-darkframes-trigger.
            yield from bps.trigger_and_read([self.device], name='dark')
            # Restage.
            yield from bps.unstage(self.device)
            # restore numcapture and shutter_enabled and num_exposures
        finally:
            yield from bps.mv(self.device.hdf5.num_capture, num_capture)
            yield from bps.mv(self.device.dg1.shutter_enabled, shutter_enabled)
            # yield from bps.mv(self.device.cam.num_exposures, num_exposures)

        try:
            # Dark frames finished, moving on to data
            yield from bps.stage(self.device)
            status = yield from bps.trigger(self.device, group='primary-trigger')
            while not status.done:
                yield from bps.trigger_and_read(self.async_poll_devices, name='labview')
                yield from bps.sleep(1)
            yield from bps.create('primary')
            yield from bps.read(self.device)
            yield from bps.save()
        finally:
            yield from bps.unstage(self.device)

    def acquire(self):
        self.RE(self._plan(), **self.metadata)
