from xicam.plugins.DataResourcePlugin import DataResourcePlugin
from xicam.gui.widgets.dataresourcebrowser import *
from alsdac import ophyd
from bluesky import RunEngine
from bluesky.plans import count
from xicam.core.data import NonDBHeader
from xicam.gui import threads
from ophyd import areadetector

from xicam.core import msg


class DataResourceAcquireView(QWidget):
    sigOpen = Signal(NonDBHeader)

    def __init__(self, model):
        super(DataResourceAcquireView, self).__init__()
        self.model = model

        self.setLayout(QFormLayout())

        self.PVname = QLineEdit('ALS:701:')
        self.layout().addWidget(self.PVname)

        self.acquirebtn = QPushButton('Acquire')
        self.acquirebtn.clicked.connect(self.acquire)
        self.layout().addWidget(self.acquirebtn)

        self.livebtn = QPushButton('Live')
        self.livebtn.clicked.connect(self.liveacquire)
        self.layout().addWidget(self.livebtn)

    def acquire(self):
        self.sigOpen.emit(self.model.dataresource.pull(self.PVname.text()))

    def liveacquire(self):
        self.model.dataresource.stream_to(self.sigOpen.emit(self.PVname.text()))


class DataResourceAcquireModel(QObject):
    def __init__(self, dataresource):
        super(DataResourceAcquireModel, self).__init__()
        self.dataresource = dataresource


class DataResourceController(QWidget):
    sigOpen = Signal(NonDBHeader)
    sigPreview = Signal(object)

    def __init__(self, view):
        super(DataResourceController, self).__init__()
        self.view = view
        self.view.sigOpen.connect(self.sigOpen)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(view)


class OphydDataResourcePlugin(DataResourcePlugin):
    model = DataResourceAcquireModel
    view = DataResourceAcquireView
    controller = DataResourceController

    def __init__(self, host=None, user=None, password=None, path=''):
        scheme = 'sftp'
        self.config = {'scheme': scheme, 'host': 'ALS:701:', 'path': path, 'user': user, 'password': password}
        super(OphydDataResourcePlugin, self).__init__(**self.config)

        self.RE = RunEngine()

    def pull(self, pvname):
        class SC(areadetector.cam.SimDetectorCam):
            pool_max_buffers = None

        class IP(areadetector.ImagePlugin):
            pool_max_buffers = None

        class Detector(areadetector.SimDetector):
            image1 = areadetector.Component(IP, 'image1:')
            cam = areadetector.Component(SC, 'cam1:')

        instrument = Detector(pvname, name=pvname, read_attrs=['image1'])
        instrument.image1.shaped_image.kind = 'normal'

        docs = {'start': [],
                'descriptor': [],
                'event': [],
                'stop': []}
        self.RE(count([instrument]), lambda doctype, doc: docs[doctype].append(doc))
        return NonDBHeader(docs['start'][0], docs['descriptor'], docs['event'], docs['stop'][0])

    @threads.method
    def stream_to(self, receiver):
        instrument = ophyd.Instrument(self.view.PVname.text(), name=self.view.PVname.text())
        print(instrument)
        self.RE(count([instrument], 100, delay=.1), receiver)

    def _showProgress(self, progress: int, maxprogress: int):
        threads.invoke_in_main_thread(msg.showProgress, progress, 0, maxprogress)
