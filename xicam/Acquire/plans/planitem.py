from appdirs import user_cache_dir
import importlib.util
import os
from xicam.core.msg import logError, logMessage, CRITICAL
from .. import runengine


class PlanItem(object):
    def __init__(self, name, icon, params, code='', plan=None):
        self.name = name
        self.icon = icon
        self.params = params
        self.code = code
        self._plan = plan

    @property
    def plan(self):
        if self._plan is None and self.code:
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

        return self._plan

    @property
    def parameter(self):
        return getattr(self.plan, 'parameter', None)

    def __reduce__(self):
        return PlanItem, (self.name, self.icon, self.params, self.code)

    def run(self, callback=None):
        runengine.RE(self.plan, callback)
