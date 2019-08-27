from xicam.plugins.dataresourceplugin import DataResourcePlugin
from xicam.gui.widgets.dataresourcebrowser import *
from xicam.plugins import manager as pluginmanager
from xicam.core.data import NonDBHeader
from ..runengine import RE
from ..plans.planitem import PlanItem
from xicam.gui.utils import ParameterDialog

class BlueskyDataResourceModel(QObject):
    def __new__(cls, datasource):
        model = pluginmanager.getPluginByName('xicam.Acquire.plans', "SettingsPlugin").plugin_object.plansmodel
        model.dataresource = datasource
        return model

class BlueskyDataResourceView(DataResourceList):
    sigOpen = Signal(NonDBHeader)

    def __init__(self, model):
        super(BlueskyDataResourceView, self).__init__(model)
        self.model = model


class BlueskyDataResourceController(QWidget):
    sigOpen = Signal(NonDBHeader)
    sigPreview = Signal(object)

    def __init__(self, view):
        super(BlueskyDataResourceController, self).__init__()
        self.view = view
        self.view.sigOpen.connect(self.sigOpen)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(view)

        self.runbutton = QPushButton('Run!')
        self.layout().addWidget(self.runbutton)
        self.runbutton.clicked.connect(self.openplan)

        self.layout().setContentsMargins(0, 0, 0, 0)

    def openplan(self):
        item = self.view.model.itemFromIndex(self.view.selectionModel().currentIndex())
        planitem = item.data(Qt.UserRole)

        # Ask for parameters
        param = planitem.parameter
        if param: ParameterDialog(param).exec_()

        self.sigOpen.emit(self.view.model.dataresource.pull(planitem))


class BlueskyDataResourcePlugin(DataResourcePlugin):
    model = BlueskyDataResourceModel
    view = BlueskyDataResourceView
    controller = BlueskyDataResourceController
    name = 'Plans'

    def __init__(self, flags: dict = None, **config):
        config['host'] = ''
        super(BlueskyDataResourcePlugin, self).__init__(flags, **config)

    def pull(self, planitem: PlanItem):
        header = NonDBHeader()

        planitem.run(lambda doctype, doc: header.append(doctype, doc))

        return header
