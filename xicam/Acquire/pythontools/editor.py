
from qtpy.QtWidgets import *
from pyqode.core import panels, api, modes
from pyqode.python import widgets, panels as pypanels, modes as pymodes
from pyqode.python.backend import server
from xicam.plugins import manager as pluginmanager
from ..runengine import RE
from ..plans.planitem import PlanItem


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

        self.addAction('Run', self.Run)
        self.addAction('Save Plan', self.SavePlan)

    def Run(self, script=None):
        if not script: script = self.editor.toPlainText()

        planitem = PlanItem('Temp', '', '', script)
        plan = planitem.plan

        RE.put(plan)


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

    def SavePlan(self):
        pluginmanager.getPluginByName('xicam.Acquire.plans', 'SettingsPlugin').plugin_object.add_plan(
            self.editor.toPlainText())


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
        self.panels.append(panels.SearchAndReplacePanel(),
                           panels.SearchAndReplacePanel.Position.BOTTOM)
        self.panels.append(panels.EncodingPanel(), api.Panel.Position.TOP)
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
        self.insertPlainText('''from bluesky.plans import scan
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

''')

    def cleanup(self):
        self.file.close()
        self.backend.stop()
