from appdirs import user_cache_dir
import importlib.util
import os
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
            exec(self.code, exec_locals)

            self._plan = exec_locals['plan']
        return self._plan

    @property
    def parameter(self):
        return getattr(self.plan, 'parameter', None)

    def __reduce__(self):
        return PlanItem, (self.name, self.icon, self.params, self.code)

    def run(self, callback=None):
        runengine.RE(self.plan, callback)
