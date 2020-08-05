from appdirs import site_config_dir, user_config_dir
from pathlib import Path

from qtpy.QtCore import QDir, Signal, Qt
from qtpy.QtGui import QIcon, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget, QLabel, QListView
from happi import Client
from happi.qt import HappiDeviceListView

from xicam.plugins import SettingsPlugin
from xicam.gui import static


# TODO: default directory -- appdirs
# TODO: what do we want to show when selecting a device?
# TODO: load ALL happi JSONs in the appdirs directories
# TODO: don't support custom locations directories yet


class HappiConfig(QWidget):

    sigRefreshDevices = Signal()

    def __init__(self, parent=None):
        super(HappiConfig, self).__init__(parent)

        layout = QVBoxLayout()
        self.databases_view = QListView()
        refresh_button = QPushButton("Refresh")
        layout.addWidget(self.databases_view)
        layout.addWidget(refresh_button)
        self.setLayout(layout)

        refresh_button.clicked.connect(self.sigRefreshDevices)


class HappiSettingsPlugin(SettingsPlugin):
    def __init__(self):
        self._happi_db_dirs = [
            site_config_dir(appname="xicam", appauthor="CAMERA"),
            user_config_dir(appname="xicam", appauthor="CAMERA")
        ]
        self._device_view = HappiDeviceListView()
        self._databases_model = QStandardItemModel()
        self._happi_config = HappiConfig()
        self._happi_config.databases_view.setModel(self._databases_model)
        for db_dir in self._happi_db_dirs:
            for db_file in Path(db_dir).glob('*.json'):
                self._databases_model.appendRow(QStandardItem(db_file.as_posix()))
        self._happi_config.databases_view.selectionModel().selectionChanged.connect(self.update_view)
        self._happi_config.sigRefreshDevices.connect(self.update_client)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._happi_config)
        layout.addWidget(self._device_view)
        widget.setLayout(layout)

        icon = QIcon(str(static.path('icons/calibrate.png')))
        name = "Devices"
        super(HappiSettingsPlugin, self).__init__(icon, name, widget)
        self.restore()

    def update_view(self, selected, deselected):
        db_index = selected.indexes()[-1]
        db_file = db_index.data(Qt.DisplayRole)
        self._update_client(db_file)

    def _update_client(self, db_file):
        self._device_view.client = Client(path=db_file)
        self._device_view.search()

    @property
    def devices_model(self):
        return self._device_view.model

    # def fromState(self, state):
    #     self._happi_config.setText(state)
    #
    # def toState(self):
    #     return self._happi_config.text()

    def update_client(self):
        # FIX
        for db_dir in self._happi_db_dirs:
            print(f"db_dir: {db_dir}")
            for db_file in Path(db_dir).glob('*.json'):
                print(f"\tdb_file: {db_file}")
                self._device_view.client = Client(path=db_file.as_posix())
                print(f"\tClient: {self._device_view.client}")
                self._device_view.search()
