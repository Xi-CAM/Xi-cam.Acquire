import os, sys
import stat
from qtpy.QtWidgets import *
from pyqode.core import panels, api, modes
from pyqode.python import widgets, panels as pypanels, modes as pymodes
from pyqode.python.backend import server
from functools import partial
from xicam.gui.threads import QThreadFuture
import subprocess
from appdirs import user_config_dir

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
        self.addAction('Create Action', self.CreateAction)

    def Run(self, script=None):
        if not script: script = self.editor.toPlainText()

        self._runthread = QThreadFuture(partial(exec, script))
        self._runthread.start()


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


    def CreateAction(self):
        p = partial(self.Run, self.editor.toPlainText())
        self.addAction('Custom Action', p)


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
        self.insertPlainText('''
# Required to allow controls manipulation in background
import asyncio
# Setup RunEngine
from bluesky import RunEngine
from bluesky.plans import scan
from ophyd.sim import det4, motor1, motor2, motor3

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

RE = RunEngine({}, context_managers=[], loop=loop)

# Set up simulated hardware.

# The 'det4' example detector a 2D Gaussian function of motor1, motor2.

# Move motor1 from 1-5 while moving motor2 from 10-50 -- both in 5 steps.
RE(scan([det4],
        motor1, 1, 5,
        motor2, 10, 50,
        5),
   print)

''')

    def cleanup(self):
        self.file.close()
        self.backend.stop()
