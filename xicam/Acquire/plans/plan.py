class Plan(object):
    def __init__(self, name, icon, params, code):
        self.name = name
        self.icon = icon
        self.params = params
        self.code = code

    def __reduce__(self):
        return Plan, (self.name, self.icon, self.params, self.code)
