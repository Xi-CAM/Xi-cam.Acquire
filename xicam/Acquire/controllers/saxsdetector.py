from xicam.SAXS.widgets.SAXSViewerPlugin import SAXSViewerPluginBase
from .areadetector import AreaDetectorController


class SAXSDetectorView(SAXSViewerPluginBase):
    ...


class SAXSDetectorController(AreaDetectorController):
    viewclass = SAXSDetectorView
