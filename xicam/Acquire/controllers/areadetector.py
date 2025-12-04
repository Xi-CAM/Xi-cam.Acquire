from bluesky.plans import count
from happi import from_container
from ophyd import Device
import numpy as np
from databroker import Broker
from pydm.widgets.checkbox import PyDMCheckbox
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.line_edit import PyDMLineEdit
from databroker.core import BlueskyRun
from qtpy.QtWidgets import QVBoxLayout, QCheckBox, QGroupBox, QFormLayout, QHBoxLayout, QPushButton
from xicam.core import msg
from xicam.gui.widgets.dynimageview import DynImageView
from xicam.gui.widgets.imageviewmixins import PixelCoordinates, Crosshair, BetterButtons, LogScaleIntensity, \
    ImageViewHistogramOverflowFix, AreaDetectorROI
from xicam.plugins import ControllerPlugin
from xicam.plugins import manager as plugin_manager

# from xicam.SAXS.processing.correction import CorrectFastCCDImage
from xicam.Acquire.runengine import get_run_engine


class ADImageView(AreaDetectorROI,
                  DynImageView,
                  PixelCoordinates,
                  Crosshair,
                  BetterButtons,
                  LogScaleIntensity,
                  ImageViewHistogramOverflowFix):
    pass


class AreaDetectorController(ControllerPlugin):
    viewclass = ADImageView
    view_kwargs = dict()

    def __init__(self, device, preprocess_enabled=True, maxfps=4):  # Note: typical query+processing+display <.2s
        super(AreaDetectorController, self).__init__(device)
        self.preprocess_enabled = preprocess_enabled
        self.RE = get_run_engine()

        self.setLayout(QVBoxLayout())

        self.coupled_devices = [device]

        self.bg_correction = QCheckBox("Background Correction")
        self.bg_correction.setChecked(True)

        self.imageview = self.viewclass(device=device, preprocess=self.preprocess, **self.view_kwargs)
        self.layout().addWidget(self.imageview)
        self.layout().addWidget(self.bg_correction)
        self.metadata = {}

        self.config_layout = QFormLayout()
        # self.config_layout.addRow('Acquire Time',
        #                           PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_time.setpoint_pvname}'))
        # self.config_layout.addRow('Acquire Period',
        #                           PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_period.setpoint_pvname}'))
        # self.config_layout.addRow('Image Mode',
        #                           PyDMEnumComboBox(init_channel=f'ca://{device.cam.image_mode.setpoint_pvname}'))
        # if hasattr(device, 'hdf5'):
        #     self.config_layout.addRow('Save Enabled',
        #                               PyDMCheckbox(init_channel=f'ca://{device.hdf5.enable.setpoint_pvname}'))
        # self.config_layout.addRow('Number of Exposures',
        #                           PyDMLineEdit(init_channel=f'ca://{device.cam.num_exposures.setpoint_pvname}'))
        # config_layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.image_mode.setpoint_pvname}'))
        # config_layout.addRow('Trigger Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.trigger_mode.setpoint_pvname}'))

        config_panel = QGroupBox('Configuration')
        config_panel.setLayout(self.config_layout)

        # Create the Acquire panel and its buttons
        acquire_layout = QVBoxLayout()
        acquire_button = QPushButton('Acquire')

        acquire_button.clicked.connect(self.acquire)
        acquire_layout.addWidget(acquire_button)

        self.abort_button = QPushButton('Abort')
        self.abort_button.clicked.connect(self.abort)
        self._ready()  # prepare the appropriate abort btn check state and styling

        acquire_layout.addWidget(self.abort_button)

        acquire_panel = QGroupBox('Acquire')
        acquire_panel.setLayout(acquire_layout)

        self.hlayout = QHBoxLayout()

        self.hlayout.addWidget(config_panel)
        self.hlayout.addWidget(acquire_panel)
        self.layout().addLayout(self.hlayout)

        # Connect relevant RE signals to update abort btn check state and styling depending on the RE state
        self.RE.sigStart.connect(self._started)
        self.RE.sigReady.connect(self._ready)

        # WIP
        # self.lutCheck = QCheckBox()
        # self.LUT = GradientWidget()
        # self.downsampleCheck = QCheckBox()
        # self.scaleCheck = QCheckBox()
        # self.rgbLevelsCheck = QCheckBox()

        # self.update_timer = QTimer()
        # self.update_timer.setInterval(1000 // maxfps)
        # self.update_timer.timeout.connect(self.updateFrame)
        # self.update_timer.start()

        # self.device.image1.shaped_image.subscribe(self.cacheFrame, 'value')

    def acquire(self):
        self.RE(count(self.coupled_devices), **self.metadata)

    def abort(self):
        self.RE.abort('Acquisition aborted by Xi-cam user.')

    def _started(self):
        self.abort_button.setEnabled(True)
        self.abort_button.setStyleSheet('background-color:red;color:white;font-weight:bold;')

    def _ready(self):
        self.abort_button.setEnabled(False)
        self.abort_button.setStyleSheet('')

    def get_dark(self, run_catalog: BlueskyRun):
        darks = np.asarray(run_catalog.dark.to_dask()[f"{self.device.name}_image"]).squeeze()
        if darks.ndim == 3:
            darks = np.mean(darks, axis=0)
        return darks

    def preprocess(self, image):
        if self.bg_correction.isChecked():
            try:
                flats = np.ones_like(image)
                darks = self.get_dark(Broker.named('local').v2[-1])
                image = image - darks
            except Exception:
                pass

        return image


class LabViewCoupledController(AreaDetectorController):
    def __init__(self, device, *args, **kwargs):
        super(LabViewCoupledController, self).__init__(device, *args, **kwargs)

        # Find coupled devices and add them so they'll be used with RE
        def from_device_container(container) -> Device:
            try:
                return from_container(container.device)
            except Exception as e:
                msg.logError(e)
                msg.logMessage(f"Error retreiving device from happi named '{container.metadata['name']}'")
                return None

        happi_settings = plugin_manager.get_plugin_by_name("happi_devices", "SettingsPlugin")

        coupled_devices = list(map(from_device_container,
                                   happi_settings.search(source='labview')))
        # coupled_devices += map(from_device_container,
        #                                happi_settings.search(
        #                                    prefix=device.prefix))

        # Remove errored from_container devices (Nones)
        coupled_devices = list(filter(lambda device: device, coupled_devices))

        self.coupled_devices += coupled_devices
