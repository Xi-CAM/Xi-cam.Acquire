from pathlib import Path
from qtpy.QtCore import Qt, QItemSelection, Signal, QModelIndex
from qtpy.QtGui import QIcon, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QVBoxLayout, QWidget, QTreeView, QAbstractItemView
from happi import Client, Device, HappiItem, from_container
from happi.backends.mongo_db import MongoBackend
from happi.backends.json_db import JSONBackend
from typhos.display import TyphosDeviceDisplay
import os

from xicam.core import msg
from xicam.core.paths import site_config_dir, user_config_dir
from xicam.plugins import SettingsPlugin, manager as pluginmanager
from xicam.gui import static

happi_site_dir = str(Path(site_config_dir) / "happi")
happi_user_dir = str(Path(user_config_dir) / "happi")

USER_MONGO = os.getenv("USER_MONGO")
PW_MONGO = os.getenv("PASSWD_MONGO")


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
        index = selected_indexes[0]
        self._activate(index)

    def _activate(self, index: QModelIndex):
        display = index.data(HappiClientModel.displayRole)  # try to get display from model

        if not display:
            happi_item = index.data(HappiClientModel.happiItemRole)
            device = from_container(happi_item)

            try:
                device.wait_for_connection()
            except TimeoutError as ex:
                msg.logError(ex)

            controller_name = happi_item.extraneous.get("controller_class", "typhos")
            controller = pluginmanager.get_plugin_by_name(controller_name, 'ControllerPlugin')
            display = controller(device)

            # Stash display back on the model
            self.model().setData(index, display, HappiClientModel.displayRole)

        self.sigShowControl.emit(display)


class HappiClientModel(QStandardItemModel):
    """Qt standard model that stores happi clients."""
    happiItemRole = Qt.UserRole + 1
    displayRole = Qt.UserRole + 2

    def __init__(self, *args, **kwargs):
        super(HappiClientModel, self).__init__(*args, **kwargs)
        self._clients = []

    def add_client(self, client: Client):
        self._clients.append(client)
        if isinstance(client.backend, JSONBackend):
            client_item = QStandardItem(client.backend.path)

        elif isinstance(client.backend, MongoBackend):
            client_item = QStandardItem(f"{client.backend._client.HOST}/{client.backend._collection.full_name}")
        self.appendRow(client_item)
        for result in client.search():
            # add an OphydItem
            self.add_device(client_item, result.item)
        client_item.setData(client)


    def add_device(self, client_item: QStandardItem, device: Device):
        device_item = QStandardItem(device.name)
        device_item.setData(device, self.happiItemRole)
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
        try:
            mongo_client = Client(MongoBackend(host='127.0.0.1',
                                               db='happi',
                                               collection='labview_static',
                                               user=USER_MONGO,
                                               pw=PW_MONGO,
                                               timeout=None))
            self._client_model.add_client(mongo_client)
        except Exception as e: #TODO catch exception properly
             msg.logError(e)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._device_view)
        widget.setLayout(layout)

        icon = QIcon(str(static.path('icons/calibrate.png')))
        name = "Devices"
        super(HappiSettingsPlugin, self).__init__(icon, name, widget)
        self._device_view.expandAll()
        self.restore()

    @property
    def devices_model(self):
        return self._client_model

    @property
    def devices_view(self):
        return self._device_view

    def search(self, **kwargs):
        """
        Searches all happi clients (see happi.client.Client.search)
        """
        results = []
        for client in self._client_model._clients:
            results += client.search(**kwargs)

        return results
