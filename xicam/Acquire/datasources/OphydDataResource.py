from xicam.plugins.dataresourceplugin import DataResourcePlugin
from xicam.gui.widgets.dataresourcebrowser import *
from xicam.plugins import manager as pluginmanager
from bluesky import RunEngine
from bluesky.plans import count
from xicam.core.data import NonDBHeader
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from qtpy.QtWidgets import QFormLayout
from xicam.Acquire.runengine import RE
from xicam.core import msg, threads


class OphydDataResourceModel(QObject):
    def __new__(cls, datasource):
        model = pluginmanager.getPluginByName('xicam.Acquire.devices', "SettingsPlugin").plugin_object.devicesmodel
        model.dataresource = datasource
        return model


class ConfigDialog(QDialog):
    def __init__(self, pvname):
        super(ConfigDialog, self).__init__()

        layout = QFormLayout()
        self.setLayout(layout)
        layout.addRow('Acquire Time', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:AcquireTime'))
        layout.addRow('Number of Images', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumImages'))
        layout.addRow('Number of Exposures', PyDMLineEdit(init_channel=f'ca://{pvname}cam1:NumExposures'))
        layout.addRow('Image Mode', PyDMEnumComboBox(init_channel=f'ca://{pvname}cam1:ImageMode'))
        layout.addRow('File Write Mode', PyDMEnumComboBox(init_channel=f'ca://{pvname}hdf1:FileWriteMode'))



class DataResourceAcquireView(DataResourceList):
    sigOpen = Signal(NonDBHeader)

    def __init__(self, model):
        super(DataResourceAcquireView, self).__init__(model)
        self.model = model


class DataResourceController(QWidget):
    sigOpen = Signal(NonDBHeader)
    sigPreview = Signal(object)

    def __init__(self, view):
        super(DataResourceController, self).__init__()
        self.view = view
        self.view.sigOpen.connect(self.sigOpen)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(view)

        self.acquirebtn = QPushButton('Acquire')
        self.acquirebtn.clicked.connect(self.acquire)
        self.layout().addWidget(self.acquirebtn)

        self.livebtn = QPushButton('Live')
        self.livebtn.clicked.connect(self.liveacquire)
        self.layout().addWidget(self.livebtn)

        self.configurebtn = QPushButton('Configure')
        self.configurebtn.clicked.connect(self.configure)
        self.layout().addWidget(self.configurebtn)

    def acquire(self):
        deviceitem = self.view.model.itemFromIndex(self.view.selectionModel().currentIndex())
        self.sigOpen.emit(self.view.model.dataresource.pull(deviceitem.device))

    def liveacquire(self):
        streaming_header = NonDBHeader()
        self.sigOpen.emit(self.PVname.text())
        self.model.dataresource.stream_to()

    def configure(self):
        deviceitem = self.view.model.itemFromIndex(self.view.selectionModel().currentIndex())

        configdialog = ConfigDialog(deviceitem.device.pvname)
        configdialog.exec_()


class OphydDataResourcePlugin(DataResourcePlugin):
    model = OphydDataResourceModel
    view = DataResourceAcquireView
    controller = DataResourceController
    name = 'Ophyd'

    def __init__(self, host=None, user=None, password=None, path=''):
        scheme = 'ophyd'
        self.config = {'scheme': scheme, 'host': 'Ophyd', 'path': path, 'user': user, 'password': password}
        super(OphydDataResourcePlugin, self).__init__(**self.config)

        self.RE = RunEngine()

    def pull(self, deviceitem):

        # instrument = Detector(pvname, name=pvname, read_attrs=['image1'])
        # instrument.image1.shaped_image.kind = 'normal'

        docs = {'start': [],
                'descriptor': [],
                'event': [],
                'resource': [],
                'datum': [],
                'stop': []}

        RE(count([deviceitem.device_obj]), lambda doctype, doc: docs[doctype].append(doc))
        return NonDBHeader(docs['start'][0], docs['descriptor'], docs['event'], docs['stop'][0])

    @threads.method
    def stream_to(self, receiver):
        instrument = ophyd.Instrument(self.view.PVname.text(), name=self.view.PVname.text())
        print(instrument)
        self.RE(count([instrument], 100, delay=.1), receiver)

    def _showProgress(self, progress: int, maxprogress: int):
        threads.invoke_in_main_thread(msg.showProgress, progress, 0, maxprogress)
