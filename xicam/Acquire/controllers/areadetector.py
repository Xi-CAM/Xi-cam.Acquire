import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime
from pyqtgraph import GradientWidget
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout, QHBoxLayout, QPushButton
from qtpy.QtCore import QTimer
from xicam.core import threads
from xicam.plugins import ControllerPlugin
from functools import partial
from xicam.core import msg
from xicam.gui.widgets.dynimageview import DynImageView
from caproto._utils import CaprotoTimeoutError
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from bluesky.plans import count
import ophyd

from xicam.Acquire.runengine import RE
import time


class AreaDetectorController(ControllerPlugin):
    viewclass = DynImageView

    def __init__(self, device, maxfps=10):
        super(AreaDetectorController, self).__init__(device)
        self.maxfps = maxfps

        self.setLayout(QVBoxLayout())

        self.imageview = self.viewclass()
        self.passive = QCheckBox('Passive Mode')
        self.passive.setChecked(True)
        self.error_text = pg.TextItem('')
        self.imageview.view.addItem(self.error_text)
        self.layout().addWidget(self.imageview)
        self.layout().addWidget(self.passive)

        pvname = device.pvname
        config_layout = QFormLayout()
        config_layout.addRow('Acquire Time', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:AcquireTime'))
        config_layout.addRow('Number of Images', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumImages'))
        config_layout.addRow('Number of Exposures', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumExposures'))
        config_layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{pvname}cam1:ImageMode'))

        config_panel = QGroupBox('Configuration')
        config_panel.setLayout(config_layout)

        acquire_layout = QVBoxLayout()
        acquire_button = QPushButton('Acquire')
        acquire_button.clicked.connect(self.acquire)
        acquire_layout.addWidget(acquire_button)

        acquire_panel = QGroupBox('Acquire')
        acquire_panel.setLayout(acquire_layout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(config_panel)
        hlayout.addWidget(acquire_panel)
        self.layout().addLayout(hlayout)

        self.thread = None
        self._last_timestamp = time.time()

        self.device.device_obj.image1.shaped_image.subscribe(partial(threads.invoke_in_main_thread, self.setFrame))

        self.passive.toggled.connect(self.setPassive)

    def update(self):
        self.thread = threads.QThreadFuture(self.getFrame, showBusy=False,
                                            callback_slot=partial(self.setFrame, autoLevels=self._autolevel),
                                            except_slot=self.setError)
        self.thread.start()

    def _trigger_thread(self):
        while True:
            while 1. / (time.time() - self._last_timestamp) > self.maxfps:
                time.sleep(.1)

            if self.passive.isChecked():
                break

            try:
                try:
                    self.device.device_obj.stage()
                except ophyd.utils.errors.RedundantStaging:
                    pass
                self.device.device_obj.trigger()
            except (RuntimeError, CaprotoTimeoutError) as ex:
                msg.logError(ex)

    def setPassive(self, passive):
        if passive:
            if self.thread:
                self.thread.cancel()
                self.thread = None
        else:
            self.thread = threads.QThreadFuture(self._trigger_thread,
                                                except_slot=lambda ex: self.device.device_obj.unstage())
            self.thread.start()

    def setFrame(self, value=None, **kwargs):
        if value is None:
            return

        # Never exceed maxfps
        if 1. / (time.time() - self._last_timestamp) > self.maxfps:
            return

        if self.imageview.image is None:
            self.imageview.setImage(value, autoHistogramRange=True, autoLevels=True)
        else:
            self.imageview.imageDisp = None
            self.error_text.setText('')
            self.imageview.image = value
            self.imageview.updateImage(autoHistogramRange=False)
            value = self.imageview.getProcessedImage()

            self.imageview.imageItem.updateImage(value)

        msg.logMessage('fps:', 1. / (time.time() - self._last_timestamp))
        self.error_text.setText(f'FPS: {1. / (time.time() - self._last_timestamp):.1f}')
        self._last_timestamp = time.time()

        # self.timer.singleShot(1. / self.maxfps * 1000, self.update)

    def setError(self, exception: Exception):
        msg.logError(exception)
        self.error_text.setText('An error occurred while connecting to this device.')

    def acquire(self):
        RE(count([self.device.device_obj]))


# TODO: add visibility checking
# not widget.visibleRegion().isEmpty():
#             return True
