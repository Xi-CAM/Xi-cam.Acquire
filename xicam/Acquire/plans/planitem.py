from appdirs import user_cache_dir
import importlib.util
import os
from xicam.core.msg import logError, logMessage, CRITICAL
from .. import runengine


class PlanItem(object):
    def __init__(self, name, icon, code='', plan=None):
        self.name = name
        self.icon = icon
        self._plan = plan
        self._code = code
        self._params = None

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        self._plan = None
        self._code = code
        self._params = None

    @property
    def plan(self):
        if self._plan:
            return self._plan

        elif self.code:
            return self._eval_plan()

        raise RuntimeError(f'This PlanItem has neither code nor a plan object associated with it: {self}')

    @property
    def parameter(self):
        if not self._params:
            self._params = getattr(self.plan, 'parameter', None)
        return self._params

    def _eval_plan(self):
        exec_locals = dict()

        # the code is expected to set "plan" to a plan
        try:
            exec(self.code, exec_locals)
        except Exception as ex:
            logMessage("The selected plan could not be loaded. The following exception occured in attempting to "
                       "evaluate the plan.", CRITICAL)
            logError(ex)
        else:
            try:
                self._plan = exec_locals['plan']
            except KeyError:
                logMessage('The selected plan does not define a variable "plan" to contain the exported plan.')
            else:
                return self._plan

    def __reduce__(self):
        return PlanItem, (self.name, self.icon, self.code)

    def run(self, callback=None):
        runengine.RE(self.plan, callback, suppress_parameters_dialog=True)
