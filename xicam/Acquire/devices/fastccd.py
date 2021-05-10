from collections import OrderedDict

import numpy as np
from ophyd import (SingleTrigger, HDF5Plugin, ImagePlugin, StatsPlugin,
                   ROIPlugin, TransformPlugin, OverlayPlugin, FilePlugin)

from ophyd.areadetector import EpicsSignalWithRBV
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.areadetector.detectors import DetectorBase
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite, FileStorePluginBase, \
    FileStoreIterativeWrite, FileStoreHDF5, FileStoreBase
from ophyd.areadetector.plugins import ProcessPlugin
from ophyd.device import FormattedComponent as FCpt
from ophyd import AreaDetector
import time as ttime
import itertools

from ophyd import Device, Component as Cpt
from ophyd.areadetector.base import (ADBase, ADComponent as ADCpt, ad_group,
                                     EpicsSignalWithRBV as SignalWithRBV)
from ophyd.areadetector.plugins import PluginBase
from ophyd.device import DynamicDeviceComponent as DDC, Staged

import bluesky.plan_stubs as bps
import bluesky_darkframes
from ophyd.utils import set_and_wait
from ophyd.signal import (EpicsSignalRO, EpicsSignal)
from ..runengine import get_run_engine


class IndirectTrigger(SingleTrigger):
    def __init__(self, *args, **kwargs):
        super(IndirectTrigger, self).__init__(*args, **kwargs)

        # Force continuous mode when staging
        self.stage_sigs.update([(self.cam.image_mode, 2)])


# compare with stats_plugin.py in
# https://github.com/NSLS-II-CSX/xf23id1_profiles/tree/master/profile_collection/startup/csx1/devices
class StatsPluginCSX(PluginBase):
    """This supports changes to time series PV names in AD 3-3

    Due to https://github.com/areaDetector/ADCore/pull/333
    """
    _default_suffix = 'Stats1:'
    _suffix_re = 'Stats\d:'
    _html_docs = ['NDPluginStats.html']
    _plugin_type = 'NDPluginStats'

    _default_configuration_attrs = (PluginBase._default_configuration_attrs + (
        'centroid_threshold', 'compute_centroid', 'compute_histogram',
        'compute_profiles', 'compute_statistics', 'bgd_width',
        'hist_size', 'hist_min', 'hist_max', 'profile_size',
        'profile_cursor')
                                    )

    bgd_width = ADCpt(SignalWithRBV, 'BgdWidth')
    centroid_threshold = ADCpt(SignalWithRBV, 'CentroidThreshold')

    centroid = DDC(ad_group(EpicsSignalRO,
                            (('x', 'CentroidX_RBV'),
                             ('y', 'CentroidY_RBV'))),
                   doc='The centroid XY',
                   default_read_attrs=('x', 'y'))

    compute_centroid = ADCpt(SignalWithRBV, 'ComputeCentroid', string=True)
    compute_histogram = ADCpt(SignalWithRBV, 'ComputeHistogram', string=True)
    compute_profiles = ADCpt(SignalWithRBV, 'ComputeProfiles', string=True)
    compute_statistics = ADCpt(SignalWithRBV, 'ComputeStatistics', string=True)

    cursor = DDC(ad_group(SignalWithRBV,
                          (('x', 'CursorX'),
                           ('y', 'CursorY'))),
                 doc='The cursor XY',
                 default_read_attrs=('x', 'y'))

    hist_entropy = ADCpt(EpicsSignalRO, 'HistEntropy_RBV')
    hist_max = ADCpt(SignalWithRBV, 'HistMax')
    hist_min = ADCpt(SignalWithRBV, 'HistMin')
    hist_size = ADCpt(SignalWithRBV, 'HistSize')
    histogram = ADCpt(EpicsSignalRO, 'Histogram_RBV')

    max_size = DDC(ad_group(EpicsSignal,
                            (('x', 'MaxSizeX'),
                             ('y', 'MaxSizeY'))),
                   doc='The maximum size in XY',
                   default_read_attrs=('x', 'y'))

    max_value = ADCpt(EpicsSignalRO, 'MaxValue_RBV')
    max_xy = DDC(ad_group(EpicsSignalRO,
                          (('x', 'MaxX_RBV'),
                           ('y', 'MaxY_RBV'))),
                 doc='Maximum in XY',
                 default_read_attrs=('x', 'y'))

    mean_value = ADCpt(EpicsSignalRO, 'MeanValue_RBV')
    min_value = ADCpt(EpicsSignalRO, 'MinValue_RBV')

    min_xy = DDC(ad_group(EpicsSignalRO,
                          (('x', 'MinX_RBV'),
                           ('y', 'MinY_RBV'))),
                 doc='Minimum in XY',
                 default_read_attrs=('x', 'y'))

    net = ADCpt(EpicsSignalRO, 'Net_RBV')
    profile_average = DDC(ad_group(EpicsSignalRO,
                                   (('x', 'ProfileAverageX_RBV'),
                                    ('y', 'ProfileAverageY_RBV'))),
                          doc='Profile average in XY',
                          default_read_attrs=('x', 'y'))

    profile_centroid = DDC(ad_group(EpicsSignalRO,
                                    (('x', 'ProfileCentroidX_RBV'),
                                     ('y', 'ProfileCentroidY_RBV'))),
                           doc='Profile centroid in XY',
                           default_read_attrs=('x', 'y'))

    profile_cursor = DDC(ad_group(EpicsSignalRO,
                                  (('x', 'ProfileCursorX_RBV'),
                                   ('y', 'ProfileCursorY_RBV'))),
                         doc='Profile cursor in XY',
                         default_read_attrs=('x', 'y'))

    profile_size = DDC(ad_group(EpicsSignalRO,
                                (('x', 'ProfileSizeX_RBV'),
                                 ('y', 'ProfileSizeY_RBV'))),
                       doc='Profile size in XY',
                       default_read_attrs=('x', 'y'))

    profile_threshold = DDC(ad_group(EpicsSignalRO,
                                     (('x', 'ProfileThresholdX_RBV'),
                                      ('y', 'ProfileThresholdY_RBV'))),
                            doc='Profile threshold in XY',
                            default_read_attrs=('x', 'y'))

    set_xhopr = ADCpt(EpicsSignal, 'SetXHOPR')
    set_yhopr = ADCpt(EpicsSignal, 'SetYHOPR')
    sigma_xy = ADCpt(EpicsSignalRO, 'SigmaXY_RBV')
    sigma_x = ADCpt(EpicsSignalRO, 'SigmaX_RBV')
    sigma_y = ADCpt(EpicsSignalRO, 'SigmaY_RBV')
    sigma = ADCpt(EpicsSignalRO, 'Sigma_RBV')
    # ts_acquiring = ADCpt(EpicsSignal, 'TS:TSAcquiring')

    ts_centroid = DDC(ad_group(EpicsSignal,
                               (('x', 'TS:TSCentroidX'),
                                ('y', 'TS:TSCentroidY'))),
                      doc='Time series centroid in XY',
                      default_read_attrs=('x', 'y'))

    # ts_control = ADCpt(EpicsSignal, 'TS:TSControl', string=True)
    # ts_current_point = ADCpt(EpicsSignal, 'TS:TSCurrentPoint')
    ts_max_value = ADCpt(EpicsSignal, 'TS:TSMaxValue')

    ts_max = DDC(ad_group(EpicsSignal,
                          (('x', 'TS:TSMaxX'),
                           ('y', 'TS:TSMaxY'))),
                 doc='Time series maximum in XY',
                 default_read_attrs=('x', 'y'))

    ts_mean_value = ADCpt(EpicsSignal, 'TS:TSMeanValue')
    ts_min_value = ADCpt(EpicsSignal, 'TS:TSMinValue')

    ts_min = DDC(ad_group(EpicsSignal,
                          (('x', 'TS:TSMinX'),
                           ('y', 'TS:TSMinY'))),
                 doc='Time series minimum in XY',
                 default_read_attrs=('x', 'y'))

    ts_net = ADCpt(EpicsSignal, 'TS:TSNet')
    # ts_num_points = ADCpt(EpicsSignal, 'TS:TSNumPoints')
    ts_read = ADCpt(EpicsSignal, 'TS:TSRead')
    ts_sigma = ADCpt(EpicsSignal, 'TS:TSSigma')
    ts_sigma_x = ADCpt(EpicsSignal, 'TS:TSSigmaX')
    ts_sigma_xy = ADCpt(EpicsSignal, 'TS:TSSigmaXY')
    ts_sigma_y = ADCpt(EpicsSignal, 'TS:TSSigmaY')
    ts_total = ADCpt(EpicsSignal, 'TS:TSTotal')
    total = ADCpt(EpicsSignalRO, 'Total_RBV')


class PutCompleteCapture(FilePlugin):
    def __init__(self, *args, **kwargs):
        super(PutCompleteCapture, self).__init__(*args, **kwargs)
        self.capture.put_complete = True


class HDF5PluginSWMR(PutCompleteCapture, HDF5Plugin):
    swmr_active = Cpt(EpicsSignalRO, 'SWMRActive_RBV')
    swmr_mode = Cpt(EpicsSignalWithRBV, 'SWMRMode')
    swmr_supported = Cpt(EpicsSignalRO, 'SWMRSupported_RBV')
    swmr_cb_counter = Cpt(EpicsSignalRO, 'SWMRCbCounter_RBV')
    _default_configuration_attrs = (HDF5Plugin._default_configuration_attrs +
                                    ('swmr_active', 'swmr_mode',
                                     'swmr_supported'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs['swmr_mode'] = 1
        # Prevent overwriting num_capture on stage
        del self.stage_sigs['num_capture']

    # TODO: check if this can be removed now
    def warmup(self):
        """
        This method is overridden to use the num_capture/continuous mode with external triggering
        """
        set_and_wait(self.enable, 1)
        sigs = OrderedDict([(self.parent.cam.array_callbacks, 1),
                            (self.parent.cam.image_mode, 'Single'),
                            (self.parent.cam.trigger_mode, 'Internal'),
                            # (self.num_capture, 1),
                            # just in case tha acquisition time is set very long...
                            (self.parent.cam.acquire_time, 1),
                            (self.parent.cam.acquire_period, 1),
                            (self.parent.cam.acquire_raw, 1)])

        original_vals = {sig: sig.get() for sig in sigs}

        for sig, val in sigs.items():
            ttime.sleep(0.1)  # abundance of caution
            set_and_wait(sig, val)

        ttime.sleep(2)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            set_and_wait(sig, val)


class AdjustedFileStorePluginBase(FileStorePluginBase):
    def stage(self):
        # Make a filename.
        filename, read_path, write_path = self.make_filename()

        # Ensure we do not have an old file open.
        if self.file_write_mode != 'Single':
            set_and_wait(self.capture, 0)
        # These must be set before parent is staged (specifically
        # before capture mode is turned on. They will not be reset
        # on 'unstage' anyway.
        self.file_path.set(write_path).wait()
        set_and_wait(self.file_name, filename)
        FileStoreBase.stage(self)

        # AD does this same templating in C, but we can't access it
        # so we do it redundantly here in Python.
        self._fn = self.file_template.get() % (read_path,
                                               filename,
                                               # file_number is *next* iteration
                                               self.file_number.get())
        self._fp = read_path
        if not self.file_path_exists.get():
            raise IOError("Path %s does not exist on IOC."
                          "" % self.file_path.get())


class AdjustedFileStoreHDF5(AdjustedFileStorePluginBase):
    def __init__(self, *args, **kwargs):
        super(AdjustedFileStoreHDF5, self).__init__(*args, **kwargs)
        self.filestore_spec = 'AD_HDF5'  # spec name stored in resource doc
        self.stage_sigs.update([('file_template', '%s%s_%6.6d.h5'),
                                ('file_write_mode', 'Stream'),
                                ('capture', 1)
                                ])

    def get_frames_per_point(self):
        return self.num_capture.get()

    def stage(self):
        super().stage()
        res_kwargs = {'frame_per_point': self.get_frames_per_point()}
        self._generate_resource(res_kwargs)


class AdjustedFileStoreHDF5IterativeWrite(AdjustedFileStoreHDF5, FileStoreIterativeWrite):
    def __init__(self, *args, **kwargs):
        super(AdjustedFileStoreHDF5IterativeWrite, self).__init__(*args, **kwargs)

    def stage(self):
        super(AdjustedFileStoreHDF5IterativeWrite, self).stage()
        self._point_counter = itertools.count()


class HDF5PluginWithFileStore(HDF5PluginSWMR, AdjustedFileStoreHDF5IterativeWrite):
    # AD v2.2.0 (at least) does not have this. It is present in v1.9.1.
    file_number_sync = None

    # file_number = Cpt(SignalWithRBV, 'AdjustedFileNumber')

    def __init__(self, *args, **kwargs):
        super(HDF5PluginWithFileStore, self).__init__(*args, **kwargs)
        self.stage_sigs.pop('capture', None)
        self.stage_sigs.pop(self.capture, None)

    def get_frames_per_point(self):
        return self.num_capture.get()

    def make_filename(self):
        # stash this so that it is available on resume
        self._ret = super().make_filename()
        return self._ret

    def stage(self):
        if np.array(self.array_size.get()).sum() == 0:
            self.warmup()
        super(HDF5PluginWithFileStore, self).stage()



class FCCDCam(AreaDetectorCam):
    sdk_version = Cpt(EpicsSignalRO, 'SDKVersion_RBV')
    firmware_version = Cpt(EpicsSignalRO, 'FirmwareVersion_RBV')
    overscan_cols = Cpt(EpicsSignalWithRBV, 'OverscanCols')
    fcric_gain = Cpt(EpicsSignalWithRBV, 'FCRICGain')
    fcric_clamp = Cpt(EpicsSignalWithRBV, 'FCRICClamp')

    readout_time = Cpt(EpicsSignal, 'ReadoutTime')

    acquire_time = ADCpt(SignalWithRBV, 'AdjustedAcquireTime')
    acquire_period = ADCpt(SignalWithRBV, 'AdjustedAcquirePeriod')
    acquire = ADCpt(EpicsSignal, 'AdjustedAcquire')
    acquire_raw = ADCpt(EpicsSignal, 'Acquire')

    initialize = ADCpt(EpicsSignal, 'Initialize')
    shutdown = ADCpt(EpicsSignal, "Shutdown")
    state = ADCpt(EpicsSignalRO, "State")

    def __init__(self, *args, temp_pv=None, **kwargs):
        self._temp_pv = temp_pv
        super().__init__(*args, **kwargs)


class FastCCDPlugin(PluginBase):
    _default_suffix = 'FastCCD1:'
    capture_bgnd = Cpt(EpicsSignalWithRBV, 'CaptureBgnd')
    enable_bgnd = Cpt(EpicsSignalWithRBV, 'EnableBgnd')
    enable_gain = Cpt(EpicsSignalWithRBV, 'EnableGain')
    enable_size = Cpt(EpicsSignalWithRBV, 'EnableSize')
    rows = Cpt(EpicsSignalWithRBV, 'Rows')  #
    row_offset = Cpt(EpicsSignalWithRBV, 'RowOffset')
    overscan_cols = Cpt(EpicsSignalWithRBV, 'OverscanCols')


class ProductionCamBase(DetectorBase):
    # # Trying to add useful info..
    cam = Cpt(FCCDCam, "cam1:")
    stats1 = Cpt(StatsPluginCSX, 'Stats1:')
    stats2 = Cpt(StatsPluginCSX, 'Stats2:')
    stats3 = Cpt(StatsPluginCSX, 'Stats3:')
    stats4 = Cpt(StatsPluginCSX, 'Stats4:')
    stats5 = Cpt(StatsPluginCSX, 'Stats5:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')
    trans1 = Cpt(TransformPlugin, 'Trans1:')
    proc1 = Cpt(ProcessPlugin, 'Proc1:')
    over1 = Cpt(OverlayPlugin, 'Over1:')
    fccd1 = Cpt(FastCCDPlugin, 'FastCCD1:')
    image1 = Cpt(ImagePlugin, 'image1:')

    # This does nothing, but it's the right place to add code to be run
    # once at instantiation time.
    def __init__(self, *arg, readout_time=0.04, **kwargs):
        self.readout_time = readout_time
        super().__init__(*arg, **kwargs)

    def pause(self):
        self.cam.acquire.put(0)
        super().pause()

    def stage(self):
        # pop both string and object versions to be paranoid
        self.stage_sigs.pop('cam.acquire', None)
        self.stage_sigs.pop(self.cam.acquire, None)

        # # we need to take the detector out of acquire mode
        # self._original_vals[self.cam.acquire] = self.cam.acquire.get()
        # set_and_wait(;lsself.cam.acquire, 0)
        # # but then watch for when detector state
        # while self.cam.detector_state.get(as_string=True) != 'Idle':
        #     ttime.sleep(.01)

        return super().stage()


class ProductionCamStandard(IndirectTrigger, ProductionCamBase):
    hdf5 = Cpt(HDF5PluginWithFileStore,
               suffix='HDF1:',
               write_path_template='/data/fccd_data/%Y/%m/%d/',
               root='/data/',
               reg=None)  # placeholder to be set on instance as obj.hdf5.reg

    def stop(self):
        self.hdf5.capture.put(0)
        return super().stop()

    def pause(self):
        set_val = 0
        set_and_wait(self.hdf5.capture, set_val)
        # val = self.hdf5.capture.get()
        ## Julien fix to ensure these are set correctly
        # print("pausing FCCD")
        # while (np.abs(val-set_val) > 1e-6):
        # self.hdf5.capture.put(set_val)
        # val = self.hdf5.capture.get()

        return super().pause()

    def resume(self):
        set_val = 1
        set_and_wait(self.hdf5.capture, set_val)  # use acquire pv here rather than disable capture
        self.hdf5._point_counter = itertools.count()
        # The AD HDF5 plugin bumps its file_number and starts writing into a
        # *new file* because we toggled capturing off and on again.
        # Generate a new Resource document for the new file.

        # grab the stashed result from make_filename
        filename, read_path, write_path = self.hdf5._ret
        self.hdf5._fn = self.hdf5.file_template.get() % (read_path,
                                                         filename,
                                                         self.hdf5.file_number.get() - 1)
        # file_number is *next* iteration
        res_kwargs = {'frame_per_point': self.hdf5.get_frames_per_point()}
        self.hdf5._generate_resource(res_kwargs)

        return super().resume()


class DelayGenerator(Device):
    trigger_enabled = Cpt(EpicsSignalWithRBV, 'TriggerEnabled')
    shutter_enabled = Cpt(EpicsSignalWithRBV, 'ShutterEnabled')
    delay_time = Cpt(EpicsSignalWithRBV,
                     'ShutterOpenDelay')  # TODO: This (and all) default values should be set on the IOC!
    initialize = Cpt(EpicsSignal, 'Initialize')
    reset = Cpt(EpicsSignal, 'Reset')
    state = Cpt(EpicsSignalRO, 'State')

    shutter_close_delay = Cpt(EpicsSignal, 'ShutterCloseDelay')


class ProductionCamTriggered(ProductionCamStandard):
    dg1 = FCpt(DelayGenerator, '{self._dg1_prefix}')

    # TODO: populate dg1_prefix using happi rather than hard coded value
    def __init__(self, *args, dg1_prefix=None, **kwargs):
        self._dg1_prefix = "ES7011:ShutterDelayGenerator:"
        super().__init__(*args, **kwargs)


class StageOnFirstTrigger(ProductionCamTriggered):
    _default_read_attrs = ['hdf5']

    def __init__(self, *args, **kwargs):
        super(StageOnFirstTrigger, self).__init__(*args, **kwargs)

    @property
    def _warmed_up(self):
        return np.array(self.hdf5.array_size.get()).sum() > 0

    def stage(self):
        if not self._warmed_up:
            self.hdf5.warmup()
        set_and_wait(self.dg1.shutter_enabled, True)
        return super(StageOnFirstTrigger, self).stage()

    def unstage(self):
        super(StageOnFirstTrigger, self).unstage()
        # self.hdf5.unstage()


def dark_plan(detector):
    # stash numcapture and shutter_enabled
    num_capture = yield from bps.rd(detector.hdf5.num_capture)
    shutter_enabled = yield from bps.rd(detector.dg1.shutter_enabled)

    # set to 1 temporarily
    detector.hdf5.num_capture.put(1)

    # Restage to ensure that dark frames goes into a separate file.
    yield from bps.unstage(detector)
    yield from bps.stage(detector)
    yield from bps.mv(detector.dg1.shutter_enabled, 2)
    # The `group` parameter passed to trigger MUST start with
    # bluesky-darkframes-trigger.
    yield from bps.trigger(detector, group='bluesky-darkframes-trigger')
    yield from bps.wait('bluesky-darkframes-trigger')
    snapshot = bluesky_darkframes.SnapshotDevice(detector)
    # Restage.
    yield from bps.unstage(detector)
    # restore numcapture and shutter_enabled
    yield from bps.mv(detector.hdf5.num_capture, num_capture)
    yield from bps.mv(detector.dg1.shutter_enabled, shutter_enabled)
    return snapshot


class DarkFrameFCCD(StageOnFirstTrigger):
    def __init__(self, *args, **kwargs):
        super(DarkFrameFCCD, self).__init__(*args, **kwargs)
        run_engine = get_run_engine()

        # Always take a fresh dark frame at the beginning of each run.
        dark_frame_preprocessor = bluesky_darkframes.DarkFramePreprocessor(
            dark_plan=dark_plan, detector=self, max_age=0)

        # # Take a dark frame if the last one we took is more than 30 seconds old.
        # dark_frame_preprocessor = bluesky_darkframes.DarkFramePreprocessor(
        #     dark_plan=dark_plan, detector=self, max_age=30)
        #
        # # Take a fresh dark frame if the last one we took *with this exposure time*
        # # is more than 30 seconds old.
        # dark_frame_preprocessor = bluesky_darkframes.DarkFramePreprocessor(
        #     dark_plan=dark_plan, detector=det, max_age=30,
        #     locked_signals=[det.exposure_time])
        #
        # # Always take a new dark frame if the exposure time was changed from the
        # # previous run, even if we took one with this exposure time on some earlier
        # # run. Also, re-take if the settings haven't changed but the last dark
        # # frame is older than 30 seconds.
        # dark_frame_preprocessor = bluesky_darkframes.DarkFramePreprocessor(
        #     dark_plan=dark_plan, detector=det, max_age=30,
        #     locked_signals=[det.exposure_time], limit=1)

        run_engine.RE.preprocessors.append(dark_frame_preprocessor)


# FastCCD = DarkFrameFCCD
FastCCD = StageOnFirstTrigger
