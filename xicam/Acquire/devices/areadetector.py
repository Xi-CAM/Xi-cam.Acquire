from ophyd import areadetector


class AreaDetector(areadetector.AreaDetector):
    image1 = areadetector.Component(areadetector.ImagePlugin, 'image1:')
    cam = areadetector.Component(areadetector.cam.AreaDetectorCam, 'cam1:')


class PilatusDetector(areadetector.PilatusDetector):
    image1 = areadetector.Component(areadetector.ImagePlugin, 'image1:')
