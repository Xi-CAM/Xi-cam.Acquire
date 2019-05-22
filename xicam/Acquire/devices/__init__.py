from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.gui.static import path
from xicam.gui.widgets.searchlineedit import SearchLineEdit
from copy import deepcopy
from collections import namedtuple

from xicam.plugins import SettingsPlugin, manager
from xicam.plugins import cammart
from collections import namedtuple
from xicam.plugins import manager as pluginmanager
from .device import Device
from .areadetector import AreaDetector

from ophyd import EpicsMotor, PilatusDetector


class DeviceSettingsPlugin(SettingsPlugin):
    """
    A built-in settings plugin to configure connections to other hosts
    """

    def __init__(self):
        # Setup UI
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.listview = QListView()
        self.devicesmodel = QStandardItemModel()
        self.listview.setModel(self.devicesmodel)

        self.plugintoolbar = QToolBar()
        self.plugintoolbar.setOrientation(Qt.Vertical)
        self.plugintoolbar.addAction(QIcon(str(path('icons/plus.png'))),
                                     'Add device',
                                     self.add_device)
        self.plugintoolbar.addAction(QIcon(str(path('icons/minus.png'))),
                                     'Remove device',
                                     self.remove_device)
        self.widget.layout().addWidget(self.listview)
        self.widget.layout().addWidget(self.plugintoolbar)
        super(DeviceSettingsPlugin, self).__init__(QIcon(str(path('icons/controlpanel.png'))),
                                                   'Devices',
                                                   self.widget)
        self.restore()

    def add_device(self):
        """
        Open the device connect dialog
        """
        self._dialog = DeviceDialog()
        self._dialog.sigAddDevice.connect(self._add_device)
        self._dialog.exec_()

    def remove_device(self):
        """
        Removes a device
        """
        if self.listview.selectedIndexes():
            self.devicesmodel.removeRow(self.listview.selectedIndexes()[0].row())

    def _add_device(self, device: Device):
        item = DeviceItem(device)
        self.devicesmodel.appendRow(item)
        self.devicesmodel.dataChanged.emit(item.index(), item.index())

    def toState(self):
        return [device.__reduce__()[1] for device in self.devices]

    def fromState(self, state):
        self.devicesmodel.clear()
        if state:
            for device in state:
                item = DeviceItem(Device(*device))
                self.devicesmodel.appendRow(item)
            self.listview.reset()

    @property
    def devices(self):
        return [self.devicesmodel.item(i).device for i in range(self.devicesmodel.rowCount())]


class DeviceDialog(QDialog):
    sigAddDevice = Signal(Device)
    sigConnect = Signal(str)

    deviceclasses = {'Epics Motor': EpicsMotor, 'Simple Area Detector (Generic)': AreaDetector,
                     'Pilatus Detector': PilatusDetector}

    def __init__(self):
        super(DeviceDialog, self).__init__()

        # Set size and position
        # self.setGeometry(0, 0, 800, 500)
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())
        self.namedynamically = True

        # Setup fields
        self.name = QLineEdit()
        self.devicestring = QLineEdit()
        self.controller = QComboBox()
        self.deviceclass = QComboBox()
        for name in self.deviceclasses:
            self.deviceclass.addItem(name)

        # TODO: add controller plugin
        # Temporary hard coded values
        for plugin in pluginmanager.getPluginsOfCategory('ControllerPlugin'):
            self.controller.addItem(plugin.name)

        # Setup dialog buttons
        self.addButton = QPushButton("&Add")
        self.connectButton = QPushButton("Test C&onnect")
        self.cancelButton = QPushButton("&Cancel")
        self.addButton.clicked.connect(self.add)
        self.connectButton.clicked.connect(self.connect)
        self.cancelButton.clicked.connect(self.close)
        self.buttonboxWidget = QDialogButtonBox()
        self.buttonboxWidget.addButton(self.addButton, QDialogButtonBox.AcceptRole)
        self.buttonboxWidget.addButton(self.connectButton, QDialogButtonBox.AcceptRole)
        self.buttonboxWidget.addButton(self.cancelButton, QDialogButtonBox.RejectRole)

        # Wireup signals
        self.devicestring.textChanged.connect(self.fillName)
        self.name.textChanged.connect(self.stopDynamicName)

        # Compose main layout
        mainLayout = QFormLayout()
        mainLayout.addRow('Device Name', self.name)
        mainLayout.addRow('Device PV', self.devicestring)
        mainLayout.addRow('Controller Type', self.controller)
        mainLayout.addRow('Device Class', self.deviceclass)
        mainLayout.addRow(self.buttonboxWidget)

        self.setLayout(mainLayout)
        self.setWindowTitle("Add Device...")

        # Set modality
        self.setModal(True)

    def fillName(self, text):
        newname = self.name.setText(text.split(':')[-1] or text.split(':')[-2])

        if self.name == '':
            self.namedynamically = True

        if self.namedynamically:
            self.name.setText(newname)

    def stopDynamicName(self, _):
        self.namedynamically = False

    def add(self):
        self.sigAddDevice.emit(
            Device(self.name.text(), self.devicestring.text(), self.controller.currentText(),
                   self.deviceclasses[self.deviceclass.currentText()]))  # EpicsMotor)) # SynAxis
        self.accept()

    def connect(self):
        # Test the connection
        ...


class ConnectDelegate(QItemDelegate):
    def __init__(self, parent):
        super(ConnectDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = QToolButton(self.parent(), )
            button.setAutoRaise(True)
            button.setText('Delete Operation')
            button.setIcon(QIcon(path('icons/trash.png')))
            sp = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            sp.setWidthForHeight(True)
            button.setSizePolicy(sp)
            button.clicked.connect(index.data())

            self._parent.setIndexWidget(index, button)


class DeviceItem(QStandardItem):
    def __init__(self, device: Device):
        super(DeviceItem, self).__init__(device.name)
        self.device = device
        self._widget = None

    @property
    def widget(self):
        if not self._widget:
            controllername = self.device.controller
            controllerclass = pluginmanager.getPluginByName(controllername, 'ControllerPlugin').plugin_object
            self._widget = controllerclass(self.device)
        return self._widget
