from ophyd.areadetector.detectors import AndorDetector
from ophyd.areadetector.base import ADComponent as C, ADBase
from ophyd import ImagePlugin, SingleTrigger, Staged, HDF5Plugin
import numpy as np
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite, FileStoreHDF5


class HDF5Warmup(ADBase):  # TODO: add this when paths are fixed
    _default_read_attrs = ['hdf5']

    @property
    def _warmed_up(self):
        return np.array(self.hdf5.array_size.get()).sum() > 0

    def stage(self):
        if not self._warmed_up:
            self.hdf5.warmup()
        return super(HDF5Warmup, self).stage()


class StageOnFirstTrigger(ADBase):
    def trigger(self):
        if self._staged == Staged.no:
            self.stage()
        super(StageOnFirstTrigger, self).trigger()


class FileStoreHDF5Plugin(FileStoreHDF5, HDF5Plugin):
    pass


class Andor(StageOnFirstTrigger, SingleTrigger, AndorDetector):
    image1 = C(ImagePlugin, 'image1:')

    def __init__(self, *args, **kwargs):
        super(Andor, self).__init__(*args, **kwargs)
        self.stage_sigs.update({'cam.image_mode': 0})

    # hdf5 = C(FileStoreHDF5Plugin,
    #            'HDF1:',
    #            write_path_template='/remote-data/fccd_data/%Y/%m/%d/',
    #            root='/remote-data/',
    #            reg=None)  # placeholder to be set on instance as obj.hdf5.reg
