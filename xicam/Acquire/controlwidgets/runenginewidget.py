from qtpy.QtWidgets import QWidget, QGridLayout, QListView, QPushButton, QSplitter, QVBoxLayout
from qtpy.QtCore import QItemSelectionModel, Qt
from qtpy.QtGui import QStandardItemModel
from xicam.plugins import manager as pluginmanager
from pyqtgraph.parametertree import ParameterTree, parameterTypes
from xicam.gui.widgets.metadataview import MetadataWidget
from functools import partial
from xicam.core import threads

empty_parameter = parameterTypes.GroupParameter(name='No parameters')


class RunEngineWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super(RunEngineWidget, self).__init__(*args, **kwargs)

        self.planview = QListView()
        self.plansmodel = pluginmanager.getPluginByName('xicam.Acquire.plans',
                                                        'SettingsPlugin').plugin_object.plansmodel  # type: QStandardItemModel
        self.planview.setModel(self.plansmodel)
        self.selectionmodel = QItemSelectionModel(self.plansmodel)
        self.planview.setSelectionModel(self.selectionmodel)

        self.parameterview = ParameterTree()

        self.metadata = MetadataWidget()

        self.runbutton = QPushButton('Run!')

        # Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.splitter = QSplitter()
        self.layout.addWidget(self.splitter)

        self.splitter.addWidget(self.planview)
        self.runwidget = QWidget()
        self.runlayout = QVBoxLayout()
        self.runlayout.setContentsMargins(0, 0, 0, 0)
        self.runlayout.addWidget(self.parameterview)
        self.runlayout.addWidget(self.runbutton)
        self.runwidget.setLayout(self.runlayout)
        self.splitter.addWidget(self.runwidget)
        self.splitter.addWidget(self.metadata)

        # Wireup signals
        self.selectionmodel.currentChanged.connect(self.showPlan)
        self.runbutton.clicked.connect(self.run)

        # Run model
        self.runmodel = QStandardItemModel()
        self.runselectionmodel = QItemSelectionModel(self.runmodel)

    def showPlan(self, current, previous):
        planitem = self.plansmodel.itemFromIndex(current).data(Qt.UserRole)
        self.parameterview.setParameters(getattr(planitem.plan, 'parameter', empty_parameter), showTop=False)

    def run(self):
        self.metadata.reset()
        planitem = self.plansmodel.itemFromIndex(self.selectionmodel.currentIndex()).data(Qt.UserRole)

        planitem.run(callback=partial(threads.invoke_in_main_thread, self.metadata.doc_consumer, force_event=True))


class MDVWithButtons(QWidget):
    def __init__(self, mdv, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mdv = mdv

    def doc_consumer(self, name, doc):
        self.mdv.doc_consumer(name, doc)
        self.spinner.setRange(0, self.mdv.headermodel.rowCount() - 1)
