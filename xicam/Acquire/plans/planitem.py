from appdirs import user_cache_dir
import importlib.util
import os
from ..runengine import RE


class PlanItem(object):
    def __init__(self, name, icon, params, code='', plan=None):
        self.name = name
        self.icon = icon
        self.params = params
        self.code = code

    @property
    def plan(self):
        plan_path = os.path.join(user_cache_dir(appname='xicam'), 'temp_plan.py')

        with open(plan_path, 'w') as plan_file:
            plan_file.write(self.code)

        spec = importlib.util.spec_from_file_location("temp_plan", plan_path)
        temp_plan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(temp_plan)

        plan = temp_plan.plan
        return plan

    @property
    def parameter(self):
        return getattr(self.plan, 'parameter', None)

    def __reduce__(self):
        return PlanItem, (self.name, self.icon, self.params, self.code)

    def run(self, callback=None):
        RE(self.plan, callback)
