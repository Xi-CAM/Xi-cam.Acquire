from bluesky.plans import scan
from bluesky_widgets.utils.streaming import stream_documents_into_runs
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.core import CallbackBase
from databroker import Broker
from databroker.core import BlueskyRun
from happi import from_container
from ophyd import Device
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.pushbutton import PyDMPushButton
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout, QHBoxLayout, QPushButton, QComboBox, QApplication, QLineEdit

from xicam.Acquire.runengine import get_run_engine
from xicam.Acquire.devices.diode import DetectorDiode
from xicam.gui.widgets.imageviewmixins import CatalogImagePlotView
from xicam.plugins import ControllerPlugin
from xicam.plugins import manager as plugin_manager
from xicam.core.msg import logError



class DiodeController(ControllerPlugin):

    def __init__(self, device: Device):
        super(DiodeController, self).__init__(device)

        self.RE = get_run_engine()
        self.plot_panel = CatalogImagePlotView(field_filter=None)

        full_layout = QHBoxLayout()
        self.setLayout(full_layout)
        config_layout = QVBoxLayout()
        scan_panel = QGroupBox('Diode Scan')
        scan_panel.setMaximumSize(200, 250)
        scan_panel.setLayout(config_layout)
        full_layout.addWidget(self.plot_panel)
        full_layout.addWidget(scan_panel)

        # get devices from happi database
        happi_settings = plugin_manager.get_plugin_by_name("happi_devices", "SettingsPlugin")
        def from_device_container(container) -> Device:
            try:
                return from_container(container.device)
            except Exception as e:
                logError(e)
                return None
        self.async_poll_devices = list(map(from_device_container,
                                           happi_settings.search(source='labview',
                                                                 device_class='ophyd.EpicsMotor')
                                           )
                                       )
        self.async_poll_devices += map(from_device_container,
                                       happi_settings.search(prefix=device.prefix))
        # Remove errored from_container devices (Nones)
        self.async_poll_devices = list(filter(lambda device: device, self.async_poll_devices))
        self.async_poll_devices.remove(device)
        self.device_dict = {device.name : device for device in self.async_poll_devices}
        # get the diode as detector
        diode = device.diode

        self.device_selector = QComboBox()
        self.device_selector.addItems(list(self.device_dict.keys()))

        input_layout = QFormLayout()
        self.start_range = QLineEdit()
        self.stop_range = QLineEdit()
        self.n_steps = QLineEdit()
        self.step_size = QLineEdit()
        input_layout.addRow('Start Range', self.start_range)
        input_layout.addRow('Stop Range', self.stop_range)
        input_layout.addRow('N Steps', self.n_steps)
        input_layout.addRow('Step Size', self.step_size)

        config_layout.addWidget(self.device_selector)
        config_layout.addLayout(input_layout)

        button_layout = QHBoxLayout()
        start_button = QPushButton("Start")
        button_layout.addWidget(start_button)
        start_button.clicked.connect(self.push_start)
        config_layout.addLayout(button_layout)

        #TODO get data from bluesky run in callback
        # runs = []
        # self.RE.subscribe(stream_documents_into_runs(self.plot_panel.setCatalog))
        # self.plot_panel.setData(runs)

        # Wireup display to receive completed runs
        self.run_dispatcher = RunDispatcher(self.plot_panel.setCatalog)

    def push_start(self):
        det = self.device
        motor = self.device_dict[self.device_selector.currentText()]
        start = float(self.start_range.text())
        stop = float(self.stop_range.text())
        steps = int(self.n_steps.text())
        self.RE(scan([det], motor, start, stop, steps), self.run_dispatcher)


class RunDispatcher(CallbackBase):
    def __init__(self, callback):
        self.callback = callback
        self._run = None
        #
        self._document_collector = stream_documents_into_runs(self.add_new_run)

    def __call__(self, name, doc, validate=False):
        self._document_collector(name, doc, validate)
        super(RunDispatcher, self).__call__(name, doc, validate)

    def add_new_run(self, run):
        self._run = run

    def stop(self, doc):
        self.callback(self._run)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = DiodeController()
    w.show()
    sys.exit(app.exec_())