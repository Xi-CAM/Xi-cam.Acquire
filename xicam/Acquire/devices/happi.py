from pathlib import Path
import os

from qtpy.QtCore import Qt, QItemSelection, Signal
from qtpy.QtGui import QIcon, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QVBoxLayout, QWidget, QTreeView, QAbstractItemView
from happi import Client, Device, HappiItem, from_container
from typhos.display import TyphosDeviceDisplay

from xicam.core import msg
from xicam.core.paths import site_config_dir, user_config_dir
from xicam.plugins import SettingsPlugin, manager as pluginmanager
from xicam.gui import static

happi_site_dir = str(Path(site_config_dir) / "happi")
happi_user_dir = str(Path(user_config_dir) / "happi")


class HappiClientTreeView(QTreeView):
    sigShowControl = Signal(QWidget)
    """Tree view that displays happi clients with any associated devices as their children."""
    def __init__(self, *args, **kwargs):
        super(HappiClientTreeView, self).__init__(*args, **kwargs)

        self.setHeaderHidden(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        selected_indexes = selected.indexes()
        if not selected_indexes:
            return
        data = selected_indexes[0].data(Qt.UserRole + 1)
        if isinstance(data, HappiItem):
            self._activate(data)

    def _activate(self, item: HappiItem):
        device = from_container(item)

        try:
            device.wait_for_connection()
        except TimeoutError as ex:
            msg.logError(ex)

        controller_name = item.extraneous.get("controller_class", "typhos")
        controller = pluginmanager.get_plugin_by_name(controller_name, 'ControllerPlugin')
        display = controller(device)
        self.sigShowControl.emit(display)


class HappiClientModel(QStandardItemModel):
    """Qt standard model that stores happi clients."""
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


class HappiSettingsPlugin(SettingsPlugin):
    def __init__(self):
        self._happi_db_dirs = [happi_site_dir, happi_user_dir]
        self._device_view = HappiClientTreeView()
        self._client_model = HappiClientModel()
        self._device_view.setModel(self._client_model)
        for db_dir in self._happi_db_dirs:
            for db_file in Path(db_dir).glob('*.json'):
                client = Client(path=str(db_file))
                self._client_model.add_client(client)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._device_view)
        widget.setLayout(layout)

        icon = QIcon(str(static.path('icons/calibrate.png')))
        name = "Devices"
        super(HappiSettingsPlugin, self).__init__(icon, name, widget)
        self.restore()

    @property
    def devices_model(self):
        return self._client_model

    @property
    def devices_view(self):
        return self._device_view
