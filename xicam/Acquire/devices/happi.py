from pathlib import Path
from qtpy.QtCore import Qt, QItemSelection, Signal, QModelIndex
from qtpy.QtGui import QIcon, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QVBoxLayout, QWidget, QTreeView, QAbstractItemView, QFormLayout, QLineEdit, QGroupBox
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
        self._backends = dict()

    def add_client(self, client: Client):
        self._backends[client.backend] = client
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
        device_item = QStandardItem(device.extraneous.get('display_name', device.name))
        device_item.setData(device, self.happiItemRole)
        client_item.appendRow(device_item)

    def remove_client(self, client: Client):
        for row in range(self.rowCount()):
            if self.item(row).data().backend == client.backend:
                self.removeRow(row)
                break
        else:
            raise ValueError(f'Client not found: {client}')
        del self._backends[client.backend]

    @property
    def clients(self):
        return list(self._backends.values())


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

        self.host = QLineEdit()
        self.db = QLineEdit()
        self.collection = QLineEdit()
        self.user = QLineEdit()
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.mongo_client = None

        form_layout = QFormLayout()
        form_layout.addRow('Host:', self.host)
        form_layout.addRow('Database name:', self.db)
        form_layout.addRow('Collection name:', self.collection)
        form_layout.addRow('User:', self.user)
        form_layout.addRow('Password:', self.pw)
        self.mongo_panel = QGroupBox()
        self.mongo_panel.setTitle('Happi Mongo Configuration')
        self.mongo_panel.setLayout(form_layout)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.mongo_panel)
        layout.addWidget(self._device_view)
        widget.setLayout(layout)

        icon = QIcon(str(static.path('icons/calibrate.png')))
        name = "Devices"
        super(HappiSettingsPlugin, self).__init__(icon, name, widget)
        self.restore()
        self._device_view.expandAll()

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
        for client in self._client_model.clients:
            results += client.search(**kwargs)

        return results

    def apply(self):
        if self.mongo_client:
            self._client_model.remove_client(self.mongo_client)
        if self.host.text() and self.db.text() and self.collection.text() and self.user.text() and self.pw.text():
            try:
                self.mongo_client = Client(MongoBackend(host=self.host.text(),
                                                   db=self.db.text(),
                                                   collection=self.collection.text(),
                                                   user=self.user.text(),
                                                   pw=self.pw.text(),
                                                   timeout=None))
                self._client_model.add_client(self.mongo_client)
                self._device_view.expandAll()
            except Exception as e: #TODO catch exception properly
                 msg.logError(e)

    def toState(self):
        self.apply()
        return dict(host=self.host.text(),
                    db=self.db.text(),
                    collection=self.collection.text(),
                    user=self.user.text(),
                    pw=self.pw.text())

    def fromState(self, state):
        for key in state:
            getattr(self, key).setText(state[key])
