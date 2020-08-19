from pathlib import Path

from qtpy.QtCore import QDir, Signal, Qt, QItemSelection
from qtpy.QtGui import QIcon, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget, QLabel, QListView, QTreeView, QAbstractItemView
from happi import Client, Device, HappiItem
from happi.qt import HappiDeviceListView
from typhos.display import TyphosDeviceDisplay


from xicam.core.paths import site_config_dir, user_config_dir
from xicam.plugins import SettingsPlugin
from xicam.gui import static


happi_site_dir = site_config_dir
happi_user_dir = user_config_dir


class HappiClientTreeView(QTreeView):
    """Tree view that displays happi clients with any associated devices as their children."""
    def __init__(self, *args, **kwargs):
        super(HappiClientTreeView, self).__init__(*args, **kwargs)

        self.setHeaderHidden(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        selected_indexes = selected.indexes()
        if not selected_indexes:
            return
        data = selected_indexes[0].data(Qt.UserRole+1)
        if isinstance(data, HappiItem):
            self._activate_device(data)
            print('yes')
        else:
            print('no')

    def _activate_device(self, device):

        # display = TyphosDeviceDisplay.from_device(device.device_class)
        from happi import from_container
        dev = from_container(device)
        display = TyphosDeviceDisplay.from_device(dev)
        display.show()


class HappiClientModel(QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(HappiClientModel, self).__init__(*args, **kwargs)
        self._clients = []

    def add_client(self, client: Client):
        self._clients += client
        client_item = QStandardItem(client.backend.path)
        client_item.setData(client)
        self.appendRow(client_item)
        for result in client.search():
            self.add_device(client_item, result.item)

    def add_device(self, client_item: QStandardItem, device: Device):
        device_item = QStandardItem(device.name)
        device_item.setData(device)
        client_item.appendRow(device_item)


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
        self._happi_db_dirs = [happi_site_dir, happi_user_dir]
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

    def update_client(self):
        # FIX
        for db_dir in self._happi_db_dirs:
            print(f"db_dir: {db_dir}")
            for db_file in Path(db_dir).glob('*.json'):
                print(f"\tdb_file: {db_file}")
                self._device_view.client = Client(path=db_file.as_posix())
                print(f"\tClient: {self._device_view.client}")
                self._device_view.search()
