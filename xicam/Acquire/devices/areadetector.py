from ophyd import areadetector


class SC(areadetector.cam.AreaDetectorCam):
    pool_max_buffers = None


class IP(areadetector.ImagePlugin):
    pool_max_buffers = None


class AreaDetector(areadetector.AreaDetector):
    image1 = areadetector.Component(IP, 'image1:')
    cam = areadetector.Component(SC, 'cam1:')
