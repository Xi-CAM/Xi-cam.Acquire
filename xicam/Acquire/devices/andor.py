from collections import OrderedDict
import time as ttime
import itertools

from ophyd.areadetector.detectors import AndorDetector
from ophyd.areadetector.base import ADComponent as C, ADBase
from ophyd import ImagePlugin, SingleTrigger, Staged, HDF5Plugin, set_and_wait, AndorDetectorCam, EpicsSignalRO, EpicsSignalWithRBV
from ophyd.sim import FakeEpicsSignal
import numpy as np
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite, FileStoreHDF5, FileStoreIterativeWrite, FileStorePluginBase
from ophyd.areadetector.plugins import ROIStatNPlugin_V23
from ophyd.utils import RedundantStaging


class FramesPerPointNumImages(FileStorePluginBase):
    def get_frames_per_point(self):
        return self.parent.cam.num_images.get()


class AndorWarmupFix(HDF5Plugin):
    @property
    def _warmed_up(self):
        return np.array(self.array_size.get()).sum() > 0

    def stage(self):
        if not self._warmed_up:
            self.warmup()
        return super(AndorWarmupFix, self).stage()

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

        ttime.sleep(10)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            set_and_wait(sig, val)

class HDF5PluginSWMR(HDF5Plugin):
    swmr_active = C(EpicsSignalRO, 'SWMRActive_RBV')
    swmr_mode = C(EpicsSignalWithRBV, 'SWMRMode')
    swmr_supported = C(EpicsSignalRO, 'SWMRSupported_RBV')
    swmr_cb_counter = C(EpicsSignalRO, 'SWMRCbCounter_RBV')
    _default_configuration_attrs = (HDF5Plugin._default_configuration_attrs +
                                    ('swmr_active', 'swmr_mode',
                                     'swmr_supported'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs['swmr_mode'] = 1
        # # Prevent overwriting num_capture on stage
        # del self.stage_sigs['num_capture']


class HDF5PluginWithFileStore(FramesPerPointNumImages, AndorWarmupFix, HDF5PluginSWMR, FileStoreHDF5IterativeWrite):
    pass

class StageOnFirstTrigger(ADBase):
    def trigger(self):
        if self._staged == Staged.no:
            self.stage()
        return super().trigger()


class TempfixAndorDetectorCam(AndorDetectorCam):
    andor_temp_status = C(EpicsSignalRO, 'AndorTempStatus_RBV', string=True)  # force string value


class Andor(StageOnFirstTrigger, SingleTrigger, AndorDetector):
    _default_read_attrs = ['hdf5', 'cam', 'roi_stat1']

    cam = C(TempfixAndorDetectorCam, 'cam1:')
    image1 = C(ImagePlugin, 'image1:')
    roi_stat1 = C(ROIStatNPlugin_V23, 'ROIStat1:1:')
    hdf5 = C(HDF5PluginWithFileStore,
               'HDF1:',
               write_path_template='/remote-data/andor_data/%Y/%m/%d/',
               root='/remote-data/',
               reg=None)  # placeholder to be set on instance as obj.hdf5.reg

    def __init__(self, *args, **kwargs):
        super(Andor, self).__init__(*args, **kwargs)
        self.stage_sigs.update({'cam.image_mode': 1})

    def stage(self):
        if self._staged in [Staged.yes, Staged.partially]:
            self.unstage()
        return super(Andor, self).stage()

    def stop(self, *, success=False):
        self._acquisition_signal.put(0)
        print('stopping')
        return super().stop()
