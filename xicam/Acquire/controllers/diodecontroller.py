from bluesky.plans import scan
from bluesky_widgets.utils.streaming import stream_documents_into_runs
from bluesky.callbacks.best_effort import BestEffortCallback
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
        self.plot_panel = CatalogImagePlotView()

        full_layout = QHBoxLayout()
        config_layout = QVBoxLayout()
        scan_panel = QGroupBox('Diode Scan')
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
        # get the diode as detector
        detector = DetectorDiode()
        diode = detector.diode

        device_selector = QComboBox()
        device_selector.addItems(self.async_poll_devices)

        input_layout = QFormLayout()
        start_range = QLineEdit()
        stop_range = QLineEdit()
        n_steps = QLineEdit()
        step_size = QLineEdit()
        input_layout.addRow('Start Range', start_range)
        input_layout.addRow('Stop Range', stop_range)
        input_layout.addRow('N Steps', n_steps)
        input_layout.addRow('Step Size', step_size)

        config_layout.addWidget(device_selector)
        config_layout.addLayout(input_layout)

        button_layout = QHBoxLayout()
        start_button = QPushButton("Start")
        button_layout.addWidget(start_button)
        start_button.clicked.connect(self.push_start(det=diode,
                                                     motor=device_selector.currentText(),
                                                     start=start_range.currentText(),
                                                     stop=stop_range.currentText(),
                                                     steps=n_steps.currentText()
                                                     )
                                     )
        config_layout.addLayout(button_layout)

        #TODO get data from bluesky run in callback
        # runs = []
        # self.RE.subscribe(stream_documents_into_runs(self.plot_panel.setCatalog))
        # self.plot_panel.setData(runs)

    def plot_data(self, name, doc):
        self.plot_panel.setCatalog(doc)


    def push_start(self, det, motor, start, stop, steps):
        self.RE(scan([det], motor, start, stop, steps, {'event': self.plot_data}))






if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = DiodeController()
    w.show()
    sys.exit(app.exec_())