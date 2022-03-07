from bluesky.plans import scan
from bluesky_widgets.utils.streaming import stream_documents_into_runs
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.core import CallbackBase
from databroker import Broker
from databroker.core import BlueskyRun
from happi import from_container
from ophyd import Device
from pydm.widgets import PyDMLabel
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.pushbutton import PyDMPushButton
from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout, QHBoxLayout, QPushButton, QComboBox, \
    QApplication, QLineEdit, QSplitter
from qtpy.QtCore import Qt
from typhos import TyphosCompositeSignalPanel
from pydm.widgets.timeplot import PyDMTimePlot

from xicam.Acquire.devices.happi import HappiSettingsPlugin
from xicam.Acquire.runengine import get_run_engine
from xicam.Acquire.devices.diode import DetectorDiode
from xicam.gui.widgets.imageviewmixins import CatalogImagePlotView
from xicam.plugins import ControllerPlugin
from xicam.plugins import manager as plugin_manager
from xicam.core.msg import logError


class PSUController(ControllerPlugin):

    def __init__(self, device: Device):
        super(PSUController, self).__init__(device)

        full_layout = QVBoxLayout()
        self.setLayout(full_layout)

        # create upper layout/widget
        top_layout = QHBoxLayout()
        # add actual widgets to the top part
        bias_clocks_typhos_panel = TyphosCompositeSignalPanel.from_device(device.bias_clocks_psu)
        fcric_fops_typhos_panel = TyphosCompositeSignalPanel.from_device(device.fcric_fops_psu)
        # typhos_panel.setMaximumHeight(50)

        state_layout = QVBoxLayout()
        state_panel = QGroupBox('PSU State')
        state_panel.setLayout(state_layout)

        state_layout.addWidget(PyDMLabel(init_channel=f'ca://{device.state.pvname}'))

        state_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.on.pvname}',
                           label='Power On'))
        state_layout.addWidget(
            PyDMPushButton(pressValue=1, init_channel=f'ca://{device.off.pvname}',
                           label='Power Off'))

        time_plot = PyDMTimePlot()
        time_plot.setTimeSpan(120)
        time_plot.addYChannel(y_channel=f'ca://{device.bias_clocks_psu.channel0.voltage.pvname}',
                              name="Bias/Clocks Out1 Voltage", color="red", lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.bias_clocks_psu.channel0.current.pvname}',
                              name="Bias/Clocks Out1 Current", color="red", lineStyle=Qt.DashLine, lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.bias_clocks_psu.channel1.voltage.pvname}',
                              name="Bias/Clocks Out2 Voltage", color="green", lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.bias_clocks_psu.channel1.current.pvname}',
                              name="Bias/Clocks Out2 Current", color="green", lineStyle=Qt.DashLine, lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.bias_clocks_psu.channel2.voltage.pvname}',
                              name="Bias/Clocks Out3 Voltage", color="blue", lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.bias_clocks_psu.channel2.current.pvname}',
                              name="Bias/Clocks Out3 Current", color="blue", lineStyle=Qt.DashLine, lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.fcric_fops_psu.channel0.voltage.pvname}',
                              name="FCRIC/FOPS Out1 Voltage", color="orange", lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.fcric_fops_psu.channel0.current.pvname}',
                              name="FCRIC/FOPS Out1 Current", color="orange", lineStyle=Qt.DashLine, lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.fcric_fops_psu.channel1.voltage.pvname}',
                              name="FCRIC/FOPS Out2 Voltage", color="yellow", lineWidth=3)
        time_plot.addYChannel(y_channel=f'ca://{device.fcric_fops_psu.channel1.current.pvname}',
                              name="FCRIC/FOPS Out2 Current", color="yellow", lineStyle=Qt.DashLine, lineWidth=3)
        time_plot.setShowLegend(True)
        full_layout.addWidget(time_plot)

        top_layout.addWidget(bias_clocks_typhos_panel)
        top_layout.addWidget(fcric_fops_typhos_panel)
        top_layout.addWidget(state_panel)

        # create lower layout/widget
        bottom_layout = QHBoxLayout()
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)
        bottom_widget.setMinimumHeight(350)
        # add actual widgets to the bottom part
        # self.plot_panel = CatalogImagePlotView(field_filter=None)
        # config_layout = QVBoxLayout()
        # scan_panel = QGroupBox('Diode Scan')
        # scan_panel.setMaximumSize(200, 250)
        # scan_panel.setLayout(config_layout)
        # bottom_layout.addWidget(self.plot_panel)
        # bottom_layout.addWidget(scan_panel)

        # # add a splitter
        # splitter = QSplitter(Qt.Vertical)
        # splitter.addWidget(top_widget)
        # splitter.addWidget(bottom_widget)

        full_layout.addLayout(top_layout)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    # get devices from happi database
    happi = HappiSettingsPlugin()
    psu = from_container(happi.search(device_class="xicam.Acquire.devices.psu.PSU")[0].device)

    w = PSUController(psu)
    w.show()
    sys.exit(app.exec_())
