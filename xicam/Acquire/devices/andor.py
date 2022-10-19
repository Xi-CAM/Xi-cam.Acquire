from collections import OrderedDict
import time as ttime

from ophyd.areadetector.detectors import AndorDetector
from ophyd.areadetector.base import ADComponent as C, ADBase
from ophyd import ImagePlugin, SingleTrigger, Staged, HDF5Plugin, set_and_wait
import numpy as np
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite, FileStoreHDF5, FileStoreIterativeWrite


class NumCaptureOverrideFix(HDF5Plugin):
    # def __init__(self, *args, **kwargs):
    #     super(NumCaptureOverrideFix, self).__init__(*args, **kwargs)
    #     # Prevent overwriting num_capture on stage
    #     self.stage_sigs['num_capture'] =

    def stage(self):
        self.stage_sigs['num_capture'] = self.parent.cam.num_images.get()
        return super(NumCaptureOverrideFix, self).stage()


class AndorWarmupFix(HDF5Plugin):
    def warmup(self):
        """
        A convenience method for 'priming' the plugin.

        The plugin has to 'see' one acquisition before it is ready to capture.
        This sets the array size, etc.
        """
        set_and_wait(self.enable, 1)
        sigs = OrderedDict([(self.parent.cam.array_callbacks, 1),
                            (self.parent.cam.image_mode, 'Single'),
                            (self.parent.cam.trigger_mode, 'Internal'),
                            # just in case tha acquisition time is set very long...
                            (self.parent.cam.acquire_time, 1),
                            # (self.parent.cam.acquire_period, 1),  # for Andor, acquire period is coupled with acquire time
                            (self.parent.cam.acquire, 1)])

        original_vals = {sig: sig.get() for sig in sigs}

        for sig, val in sigs.items():
            ttime.sleep(0.1)  # abundance of caution
            set_and_wait(sig, val)

        ttime.sleep(2)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            set_and_wait(sig, val)


class FileStoreHDF5Plugin(NumCaptureOverrideFix, AndorWarmupFix, FileStoreHDF5IterativeWrite, HDF5Plugin):
    pass


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
        return super(StageOnFirstTrigger, self).trigger()


class Andor(StageOnFirstTrigger, SingleTrigger, HDF5Warmup, AndorDetector):
    image1 = C(ImagePlugin, 'image1:')

    def __init__(self, *args, **kwargs):
        super(Andor, self).__init__(*args, **kwargs)
        self.stage_sigs.update({'cam.image_mode': 1})

    hdf5 = C(FileStoreHDF5Plugin,
               'HDF1:',
               write_path_template='/remote-data/andor_data/%Y/%m/%d/',
               root='/remote-data/',
               reg=None)  # placeholder to be set on instance as obj.hdf5.reg
