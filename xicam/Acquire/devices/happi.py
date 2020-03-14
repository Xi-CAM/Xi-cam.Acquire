from qtpy.QtCore import QDir, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget
from happi import Client
from happi.qt import HappiDeviceListView

from xicam.plugins import SettingsPlugin
from xicam.gui import static


# TODO: default directory
# TODO: what do we want to show when selecting a device?
# TODO: can u load only one happi config file, or multiple?
# TODO: debug creation of happi db file (we shouldn't allow direct modification of these files tho)


class HappiConfig(QWidget):

    sigConfigChanged = Signal(str)

    def __init__(self, parent=None):
        super(HappiConfig, self).__init__(parent)

        layout = QHBoxLayout()
        self._lineedit = QLineEdit()
        self._browse_button = QPushButton("Browse")
        layout.addWidget(self._lineedit)
        layout.addWidget(self._browse_button)
        self.setLayout(layout)

        self._config_dialog = QFileDialog(self)
        self._config_dialog.setAcceptMode(QFileDialog.AcceptOpen)
        self._config_dialog.setFileMode(QFileDialog.ExistingFile)
        self._config_dialog.setDirectory(QDir.home())
        self._config_dialog.setNameFilter("Happi config file (*.json)")

        self._browse_button.clicked.connect(self._config_dialog.exec)
        self._config_dialog.accepted.connect(self.accept)

    def accept(self):
        self.setText(self._config_dialog.selectedFiles()[0])

    def setText(self, text):
        self._lineedit.setText(text)
        self.sigConfigChanged.emit(text)

    def text(self):
        return self._lineedit.text()


class HappiSettingsPlugin(SettingsPlugin):
    def __init__(self):
        self._device_view = HappiDeviceListView()
        self._happi_config = HappiConfig()
        self._happi_config.sigConfigChanged.connect(self.update_client)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._device_view)
        layout.addWidget(self._happi_config)
        widget.setLayout(layout)

        icon = QIcon(str(static.path('icons/calibrate.png')))
        name = "TEST Devices"
        super(HappiSettingsPlugin, self).__init__(icon, name, widget)
        self.restore()

    @property
    def devices_model(self):
        return self._device_view.model

    def fromState(self, state):
        self._happi_config.setText(state)

    def toState(self):
        return self._happi_config.text()

    def update_client(self, text):
        print('blah')
        self._device_view.client = Client(path=text)
        self._device_view.search()
