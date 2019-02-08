from xicam.plugins.DataResourcePlugin import DataResourcePlugin
from urllib import parse
import pysftp
import tempfile
import os
import stat
from functools import partial
from xicam.gui import threads
from xicam.gui.connections import CredentialDialog
from qtpy.QtWidgets import *
from xicam.gui.widgets.dataresourcebrowser import *
from alsdac import ophyd
from bluesky import RunEngine
from bluesky.plans import count
from xicam.core.data import NonDBHeader

from xicam.core import msg


class DataResourceAcquireView(QPushButton):
    sigOpen = Signal(NonDBHeader)

    def __init__(self, model):
        super(DataResourceAcquireView, self).__init__()
        self.setText('Acquire')
        self.model = model
        self.clicked.connect(self.acquire)

    def acquire(self):
        self.sigOpen.emit(self.model.dataresource.pull())


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
        self.config = {'scheme': scheme, 'host': 'ptGreyInstrument', 'path': path, 'user': user, 'password': password}
        super(OphydDataResourcePlugin, self).__init__(**self.config)

        self.RE = RunEngine()
        self.instrument = ophyd.Instrument('beamline:instruments:ptGreyInstrument', name='ptGreyInstrument')

    def pull(self):
        docs = {'start': [],
                'descriptor': [],
                'event': [],
                'stop': []}
        self.RE(count([self.instrument]), lambda doctype, doc: docs[doctype].append(doc))
        return NonDBHeader(docs['start'][0], docs['descriptor'], docs['event'], docs['stop'][0])

    def _showProgress(self, progress: int, maxprogress: int):
        threads.invoke_in_main_thread(msg.showProgress, progress, 0, maxprogress)
