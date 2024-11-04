import yaml

from qtpy.QtWidgets import QWidget, QListView, QPushButton, QSplitter, QVBoxLayout
from qtpy.QtCore import QItemSelectionModel, Qt, QMimeData
from qtpy.QtGui import QStandardItemModel, QClipboard, QGuiApplication
from xicam.plugins import manager as pluginmanager
from pyqtgraph.parametertree import ParameterTree, parameterTypes
from xicam.gui.widgets.metadataview import MetadataWidget
from functools import partial
from xicam.core import threads, msg
from xicam.Acquire.runengine import get_run_engine

empty_parameter = parameterTypes.GroupParameter(name='No parameters')


class RunEngineWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super(RunEngineWidget, self).__init__(*args, **kwargs)

        self.planview = QListView()
        self.plansmodel = pluginmanager.get_plugin_by_name('plans',
                                                           'SettingsPlugin').plansmodel  # type: QStandardItemModel
        self.planview.setModel(self.plansmodel)
        self.selectionmodel = QItemSelectionModel(self.plansmodel)
        self.planview.setSelectionModel(self.selectionmodel)

        self.parameterview = ParameterTree()

        self.metadata = MetadataWidget()

        self.copybutton = QPushButton('\u2398' + ' Copy parameters to clipboard')
        self.runbutton = QPushButton('Run')
        self.pausebutton = QPushButton('Pause')
        self.resumebutton = QPushButton('Resume')
        self.abortbutton = QPushButton('Abort')
        self.abortbutton.setStyleSheet('background-color:red;color:white;font-weight:bold;')

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
        self.runlayout.addWidget(self.copybutton)
        self.runlayout.addWidget(self.runbutton)
        self.runlayout.addWidget(self.pausebutton)
        self.runlayout.addWidget(self.resumebutton)
        self.runlayout.addWidget(self.abortbutton)
        self.runwidget.setLayout(self.runlayout)
        self.splitter.addWidget(self.runwidget)
        self.splitter.addWidget(self.metadata)

        # Set initial states
        self._resumed()
        self._finished()

        # Wireup signals
        self.selectionmodel.currentChanged.connect(self.showPlan)
        self.plansmodel.dataChanged.connect(self.showPlan)
        self.copybutton.clicked.connect(self.copy)
        self.runbutton.clicked.connect(self.run)
        self.abortbutton.clicked.connect(self.abort)
        self.pausebutton.clicked.connect(self.pause)
        self.resumebutton.clicked.connect(self.resume)

        self.RE = get_run_engine()
        self.RE.sigPause.connect(self._paused)
        self.RE.sigResume.connect(self._resumed)
        self.RE.sigFinish.connect(self._finished)
        self.RE.sigStart.connect(self._started)
        self.RE.sigAbort.connect(self._aborted)

        # Run model
        self.runmodel = QStandardItemModel()
        self.runselectionmodel = QItemSelectionModel(self.runmodel)
        self._current_planitem = None

    def showPlan(self):
        self._current_planitem = None
        current = self.selectionmodel.currentIndex()
        if current.isValid():
            planitem = self.plansmodel.itemFromIndex(current).data(Qt.UserRole)
            self._current_planitem = planitem

        if self._current_planitem:
            self.parameterview.setParameters(getattr(planitem, 'parameter', empty_parameter), showTop=False)
        else:
            self.parameterview.clear()

    def copy(self):
        self.metadata.reset()
        planitem = self.plansmodel.itemFromIndex(
            self.selectionmodel.currentIndex()
        ).data(Qt.UserRole)
        parameter_dict = planitem.parameter.saveState(filter='user')["children"]
        run_params_str = ""
        keys_list = list(parameter_dict.keys())  # Convert to a list
        n = 0
        while n < len(keys_list):
            if any(word in parameter_dict[keys_list[n]]["name"].lower() for word in ["start", "min"]):
                if n + 1 < len(keys_list) and any(
                        word in parameter_dict[keys_list[n + 1]]["name"].lower() for word in ["end", "max"]):
                    run_params_str += parameter_dict[keys_list[n]]["name"] + " = " + str(
                        parameter_dict[keys_list[n]]["value"]) + "\t"
                    run_params_str += parameter_dict[keys_list[n + 1]]["name"] + " = " + str(
                        parameter_dict[keys_list[n + 1]]["value"]) + "\n"
                    n += 2  # Skip the next iteration
                else:
                    run_params_str += parameter_dict[keys_list[n]]["name"] + " = " + str(
                        parameter_dict[keys_list[n]]["value"]) + "\n"
                    n += 1
            else:
                run_params_str += parameter_dict[keys_list[n]]["name"] + " = " + str(
                    parameter_dict[keys_list[n]]["value"]) + "\n"
                n += 1

        # Copy the string to the clipboard
        mime = QMimeData()
        mime.setText(run_params_str)
        mime.setData('xicam', yaml.dump(parameter_dict).encode('utf-8'))
        QGuiApplication.clipboard().setMimeData(mime)
        msg.logMessage("Copied to clipboard:\n" + run_params_str, level=msg.INFO)
        msg.notifyMessage('Plan parameters copied to clipboard!')

    def run(self):
        self.metadata.reset()
        planitem = self.plansmodel.itemFromIndex(self.selectionmodel.currentIndex()).data(Qt.UserRole)

        planitem.run(callback=partial(threads.invoke_in_main_thread, self.metadata.doc_consumer, force_event=True))

    def abort(self):
        self.RE.abort('Aborted by Xi-cam user.')

    def pause(self):
        self.RE.pause()

    def resume(self):
        self.RE.resume()
        self.resumebutton.setEnabled(False)

    def _resumed(self):
        self.resumebutton.setVisible(False)
        self.resumebutton.setEnabled(True)
        self.pausebutton.setVisible(True)

    def _paused(self):
        self.resumebutton.setVisible(True)
        self.pausebutton.setVisible(False)

    def _started(self):
        self.abortbutton.setEnabled(True)
        self.pausebutton.setEnabled(True)
        self._resumed()

    def _finished(self):
        self.abortbutton.setEnabled(False)
        self.pausebutton.setEnabled(False)

    def _aborted(self):
        self._finished()


class MDVWithButtons(QWidget):
    def __init__(self, mdv, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mdv = mdv

    def doc_consumer(self, name, doc):
        self.mdv.doc_consumer(name, doc)
        self.spinner.setRange(0, self.mdv.headermodel.rowCount() - 1)
