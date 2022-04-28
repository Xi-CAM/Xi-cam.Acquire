import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
from PyQt5.QtWidgets import QProgressBar
from pyqtgraph import GradientWidget
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout, QHBoxLayout, QPushButton
from qtpy.QtCore import QTimer
from xicam.core import threads
from xicam.plugins import ControllerPlugin
from functools import partial
from xicam.core import msg
from xicam.gui.widgets.dynimageview import DynImageView
from xicam.gui.widgets.imageviewmixins import PixelCoordinates, Crosshair, BetterButtons, LogScaleIntensity, \
    ImageViewHistogramOverflowFix, AreaDetectorROI
from caproto._utils import CaprotoTimeoutError
from ophyd.signal import ConnectionTimeoutError
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.pushbutton import PyDMPushButton
from bluesky.plans import count
import ophyd
from xicam.Acquire.runengine import RE
from timeit import default_timer
from contextlib import contextmanager
# from xicam.SAXS.processing.correction import CorrectFastCCDImage
from xicam.Acquire.runengine import get_run_engine
import time

from typing import Callable


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

    def __init__(self, device, preprocess_enabled=True, maxfps=4):  # Note: typical query+processing+display <.2s
        super(AreaDetectorController, self).__init__(device)
        self.preprocess_enabled = preprocess_enabled
        self.RE = get_run_engine()

        self.setLayout(QVBoxLayout())

        self.coupled_devices = []

        self.bg_correction = QCheckBox("Background Correction")
        self.bg_correction.setChecked(True)

        self.imageview = self.viewclass(device=device, preprocess=self.preprocess)
        self.layout().addWidget(self.imageview)
        self.layout().addWidget(self.bg_correction)
        self.metadata = {}

        config_layout = QFormLayout()
        config_layout.addRow('Acquire Time',
                             PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_time.setpoint_pvname}'))
        config_layout.addRow('Acquire Period',
                             PyDMLineEdit(init_channel=f'ca://{device.cam.acquire_period.setpoint_pvname}'))
        config_layout.addRow('Number of Images',
                             PyDMLineEdit(init_channel=f'ca://{device.hdf5.num_capture.setpoint_pvname}'))
        config_layout.addRow('Number of Exposures',
                             PyDMLineEdit(init_channel=f'ca://{device.cam.num_exposures.setpoint_pvname}'))
        # config_layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.image_mode.setpoint_pvname}'))
        # config_layout.addRow('Trigger Mode', PyDMEnumComboBox(init_channel=f'ca://{device.cam.trigger_mode.setpoint_pvname}'))

        config_panel = QGroupBox('Configuration')
        config_panel.setLayout(config_layout)

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

    def preprocess(self, image):
        return image

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
