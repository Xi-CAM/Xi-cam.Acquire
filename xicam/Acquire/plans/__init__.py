from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.gui.static import path

from xicam.plugins import SettingsPlugin, manager
from xicam.plugins import manager as pluginmanager
from .planitem import PlanItem

from ophyd.sim import SynAxis


class PlanSettingsPlugin(SettingsPlugin):
    """
    A built-in settings plugin to configure connections to other hosts
    """

    def __init__(self):
        # Setup UI
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.listview = QListView()
        self.listview.setItemDelegateForColumn(1, PlanDelegate(self.listview))
        self.plansmodel = QStandardItemModel()
        self.listview.setModel(self.plansmodel)

        self.plugintoolbar = QToolBar()
        self.plugintoolbar.setOrientation(Qt.Vertical)
        self.plugintoolbar.addAction(QIcon(str(path('icons/plus.png'))),
                                     'Add plan',
                                     self.add_plan)
        self.plugintoolbar.addAction(QIcon(str(path('icons/minus.png'))),
                                     'Remove plan',
                                     self.remove_plan)
        self.widget.layout().addWidget(self.listview)
        self.widget.layout().addWidget(self.plugintoolbar)
        super(PlanSettingsPlugin, self).__init__(QIcon(str(path('icons/controlpanel.png'))),
                                                 'Plans',
                                                 self.widget)

        self.restore()

    def add_plan(self, code=''):
        """
        Open the plan connect dialog
        """
        self._dialog = PlanDialog(code)
        self._dialog.sigAddPlan.connect(self._add_plan)
        self._dialog.exec_()

    def remove_plan(self):
        """
        Removes a plan
        """
        if self.listview.selectedIndexes():
            self.plansmodel.removeRow(self.listview.selectedIndexes()[0].row())

    def _add_plan(self, plan: PlanItem, save=True):
        item = QStandardItem(plan.name)
        item.setData(plan, Qt.UserRole)
        self.plansmodel.appendRow(item)
        self.plansmodel.dataChanged.emit(item.index(), item.index())
        if save:
            self.save()

    def toState(self):
        return self.plans

    def fromState(self, state):
        self.plansmodel.clear()
        if state:
            for plan in state:
                self._add_plan(plan, save=False)
            self.listview.reset()

    @property
    def plans(self):
        return [self.plansmodel.item(i).data(Qt.UserRole) for i in range(self.plansmodel.rowCount())]


class PlanDialog(QDialog):
    sigAddPlan = Signal(PlanItem)
    sigConnect = Signal(str)

    def __init__(self, code=''):
        super(PlanDialog, self).__init__()

        # Set size and position
        # self.setGeometry(0, 0, 800, 500)
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

        # Setup fields
        self.name = QLineEdit()
        self.icon = QLineEdit()
        self.params = QLineEdit()
        self.code = QTextEdit()

        self.code.setText(code)

        # Setup dialog buttons
        self.addButton = QPushButton("&Add")
        self.simulateButton = QPushButton("&Simulate")
        self.cancelButton = QPushButton("&Cancel")
        self.addButton.clicked.connect(self.add)
        self.simulateButton.clicked.connect(self.simulate)
        self.cancelButton.clicked.connect(self.close)
        self.buttonboxWidget = QDialogButtonBox()
        self.buttonboxWidget.addButton(self.addButton, QDialogButtonBox.AcceptRole)
        self.buttonboxWidget.addButton(self.simulateButton, QDialogButtonBox.AcceptRole)
        self.buttonboxWidget.addButton(self.cancelButton, QDialogButtonBox.RejectRole)

        # Compose main layout
        mainLayout = QFormLayout()
        mainLayout.addRow('Plan Name', self.name)
        mainLayout.addRow('Plan Icon', self.icon)
        mainLayout.addRow('Plan Params', self.params)
        mainLayout.addRow('Plan', self.code)
        mainLayout.addRow(self.buttonboxWidget)

        self.setLayout(mainLayout)
        self.setWindowTitle("Add Plan...")

        # Set modality
        self.setModal(True)

    def add(self):
        self.sigAddPlan.emit(PlanItem(self.name.text(), self.icon.text(), self.params.text(), self.code.toPlainText()))
        self.accept()

    def simulate(self):
        # Test the plan
        ...


class PlanDelegate(QItemDelegate):
    def __init__(self, parent):
        super(PlanDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = QToolButton(self.parent(), )
            button.setAutoRaise(True)
            button.setText('Delete Plan')
            button.setIcon(QIcon(path('icons/trash.png')))
            sp = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            sp.setWidthForHeight(True)
            button.setSizePolicy(sp)
            button.clicked.connect(index.data())

            self._parent.setIndexWidget(index, button)

