from ophyd import areadetector, SingleTrigger


class AreaDetector(SingleTrigger, areadetector.AreaDetector):
    _default_read_attrs = ['image1']
    image1 = areadetector.Component(areadetector.ImagePlugin, 'image1:')
    cam1 = areadetector.Component(areadetector.cam.AreaDetectorCam, 'cam1:')

    def __init__(self, *args, **kwargs):
        super(AreaDetector, self).__init__(*args, **kwargs)
        self._acquisition_signal = self.cam1.acquire


class PilatusDetector(areadetector.PilatusDetector):
    image1 = areadetector.Component(areadetector.ImagePlugin, 'image1:')
