from xicam.plugins.DataResourcePlugin import DataResourcePlugin
from xicam.gui.widgets.dataresourcebrowser import *
from xicam.plugins import manager as pluginmanager
from xicam.core.data import NonDBHeader
from ..runengine import queue_and_sub


class BlueskyDataResourceModel(QObject):
    def __init__(self, dataresource):
        super(BlueskyDataResourceModel, self).__init__()
        self.dataresource = dataresource


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


class BlueskyDataResourcePlugin(DataResourcePlugin):
    model = pluginmanager.getPluginByName('xicam.Acquire.plans', "SettingsPlugin").plugin_object.plansmodel
    view = BlueskyDataResourceView
    controller = BlueskyDataResourceController

    def pull(self, plan):
        queue_and_sub(plan, self.view.sigOpen(NonDBHeader))
