
from qtpy.QtWidgets import *
from pyqode.core import panels, api, modes
from pyqode.python import widgets, panels as pypanels, modes as pymodes
from pyqode.python.backend import server
from xicam.plugins import manager as pluginmanager
from ..runengine import get_run_engine
from ..plans.planitem import PlanItem

STUB_PLAN = '''from bluesky.plans import scan
from ophyd.sim import det4, motor1, motor2, motor3
from pyqtgraph.parametertree.parameterTypes import SimpleParameter
from xicam.gui.utils import ParameterizablePlan

min1 = SimpleParameter(name='Axis 1 Min', type='float')
min2 = SimpleParameter(name='Axis 2 Min', type='float')
max2 = SimpleParameter(name='Axis 2 Max', type='float')
max1 = SimpleParameter(name='Axis 1 Max', type='float')
steps = SimpleParameter(name='Steps', type='int')

scan = ParameterizablePlan(scan)

plan = scan([det4],
            motor1, min1, max1,
            motor2, min2, max2,
            steps)

'''

class scripteditor(QWidget):
    def __init__(self):
        super(scripteditor, self).__init__()
        scripteditoriteminstance = scripteditoritem()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(scripteditortoolbar(scripteditoriteminstance))
        self.layout().addWidget(scripteditoriteminstance)



class scripteditortoolbar(QToolBar):
    def __init__(self, editor):
        '''

        Parameters
        ----------
        editor  :   scripteditor
        '''
        super(scripteditortoolbar, self).__init__()
        self.editor = editor

        self.addAction('New', self.New)
        self.addAction('Open', self.Open)
        self.addAction('Save', self.Save)
        self.addAction('Rename', self.Rename)
        self.addAction('Run', self.Run)
        self.current_name = QLabel()
        self.addWidget(self.current_name)
        self.RE = get_run_engine()
        self.plan = PlanItem('Untitled', '', '', STUB_PLAN)
        self.set_plan(self.plan)

    def set_plan(self, plan: PlanItem):
        self.plan = plan
        self.editor.setPlainText(self.plan.code)
        self.current_name.setText(f'Editing: {self.plan.name}')

    def New(self):
        result = QMessageBox.question(self,
                                      'Unsaved changes in plan editor',
                                      f"Do you want to save changes to {self.plan.name}?",
                                      buttons=QMessageBox.StandardButtons(
                                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel),
                                      defaultButton=QMessageBox.Yes)
        if result == QMessageBox.Yes:
            if not self.Save():
                return
        elif result == QMessageBox.Cancel:
            return

        self.set_plan(PlanItem('Untitled', '', '', STUB_PLAN))

    def Open(self):
        plans = pluginmanager.get_plugin_by_name('plans', 'SettingsPlugin').plans
        if not plans:
            QMessageBox.critical(self, "No saved plans", 'There are no plans currently saved. A plan cannot be opened.')
            return
        plan_names = list(plans.keys())
        plan_name, ok = QInputDialog.getItem(self, "Open a plan...", "Select a plan to edit:", plan_names)
        if ok and plan_name:
            self.set_plan(plans[plan_name])

    def Save(self):
        self.plan.code = self.editor.toPlainText()
        if self.plan.name == 'Untitled':
            if not self.Rename():
                return
        plan_settings = pluginmanager.get_plugin_by_name('plans', 'SettingsPlugin')
        if self.plan.name not in plan_settings.plans:
            plan_settings._add_plan(self.plan)
        plan_settings.update_plan(self.plan)

        return True

    def Rename(self):
        plan_name, ok = QInputDialog.getText(self, "Rename plan...", "Enter a new name for this plan:",
                                             text=self.plan.name)
        if not ok:
            return
        while not plan_name or plan_name in pluginmanager.get_plugin_by_name('plans',
                                                                             'SettingsPlugin').plans or plan_name == 'Untitled':
            plan_name, ok = QInputDialog.getText(self, "Rename plan...",
                                                 "The entered name already exists or is invalid. Please choose a new name:",
                                                 text=self.plan.name)
            if not ok:
                return

        self.plan.name = plan_name
        self.set_plan(self.plan)
        pluginmanager.get_plugin_by_name('plans', 'SettingsPlugin').update_plan(self.plan)
        return True

    def Run(self, script=None):
        if not script: script = self.editor.toPlainText()

        planitem = PlanItem('Temp', '', '', script)
        plan = planitem.plan

        self.RE.put(plan)


        # tmpdir = user_config_dir('xicam/tmp')
        #
        # if not os.path.isdir(tmpdir): os.mkdir(tmpdir)
        #
        # tmppath = os.path.join(tmpdir,'tmp.py')
        #
        # with open(tmppath,'w') as f:
        #     f.write(script)
        #     # f.close()
        #
        # st = os.stat(tmppath)
        # os.chmod(tmppath, st.st_mode | stat.S_IEXEC)
        #
        # subprocess.call([sys.executable, tmppath])


class scripteditoritem(widgets.PyCodeEditBase):
    def __init__(self):
        super(scripteditoritem, self).__init__()

        # starts the default pyqode.python server (which enable the jedi code
        # completion worker).
        self.backend.start(server.__file__)

        # some other modes/panels require the analyser mode, the best is to
        # install it first
        # self.modes.append(pymodes.DocumentAnalyserMode())

        # --- core panels
        self.panels.append(panels.FoldingPanel())
        self.panels.append(panels.LineNumberPanel())
        self.panels.append(panels.CheckerPanel())
        # self.panels.append(panels.SearchAndReplacePanel(),
        #                    panels.SearchAndReplacePanel.Position.BOTTOM)
        # self.panels.append(panels.EncodingPanel(), api.Panel.Position.TOP)
        # add a context menu separator between editor's
        # builtin action and the python specific actions
        self.add_separator()

        # --- python specific panels
        self.panels.append(pypanels.QuickDocPanel(), api.Panel.Position.BOTTOM)

        # --- core modes
        self.modes.append(modes.CaretLineHighlighterMode())
        self.modes.append(modes.CodeCompletionMode())
        self.modes.append(modes.ExtendedSelectionMode())
        self.modes.append(modes.FileWatcherMode())
        self.modes.append(modes.OccurrencesHighlighterMode())
        self.modes.append(modes.RightMarginMode())
        self.modes.append(modes.SmartBackSpaceMode())
        self.modes.append(modes.SymbolMatcherMode())
        self.modes.append(modes.ZoomMode())
        self.modes.append(modes.PygmentsSyntaxHighlighter(self.document()))

        # ---  python specific modes
        self.modes.append(pymodes.CommentsMode())
        self.modes.append(pymodes.CalltipsMode())
        self.modes.append(pymodes.FrostedCheckerMode())
        self.modes.append(pymodes.PEP8CheckerMode())
        self.modes.append(pymodes.PyAutoCompleteMode())
        self.modes.append(pymodes.PyAutoIndentMode())
        self.modes.append(pymodes.PyIndenterMode())

        self.syntax_highlighter.color_scheme = api.ColorScheme('darcula')

        QApplication.instance().aboutToQuit.connect(self.cleanup)  # TODO: use this approach in Xi-cam

        # self.file.open('test.py')
        self.insertPlainText(STUB_PLAN)

    def cleanup(self):
        self.file.close()
        self.backend.stop()
