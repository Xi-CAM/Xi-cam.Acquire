import time as ttime
import itertools

from ophyd import (EpicsScaler, EpicsSignal, EpicsSignalRO, Device,
                   SingleTrigger, HDF5Plugin, ImagePlugin, StatsPlugin,
                   ROIPlugin, TransformPlugin, OverlayPlugin)

from ophyd import Component as Cpt
from ophyd import AreaDetector
from ophyd.areadetector import ADComponent, EpicsSignalWithRBV
from ophyd.areadetector.base import (ADBase, ADComponent as ADCpt, ad_group,
                                     EpicsSignalWithRBV as SignalWithRBV)
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.areadetector.detectors import DetectorBase
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite
from ophyd.areadetector.plugins import PluginBase, ProcessPlugin
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus

from ophyd.device import FormattedComponent as FCpt
from ophyd.device import DynamicDeviceComponent as DDC, Staged
from ophyd.utils import set_and_wait
from ophyd.sim import NullStatus
from ophyd.signal import (Signal, EpicsSignalRO, EpicsSignal)
from ophyd.quadem import QuadEM


#TODO: fccd.hdf5.filestore_spec = 'BLAHBLAH'

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


class StandardCam(SingleTrigger, AreaDetector):
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')
    # proc1 = Cpt(ProcessPlugin, 'Proc1:')
    # trans1 = Cpt(TransformPlugin, 'Trans1:')


class NoStatsCam(SingleTrigger, AreaDetector):
    pass


class HDF5PluginSWMR(HDF5Plugin):
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


class HDF5PluginWithFileStore(HDF5PluginSWMR, FileStoreHDF5IterativeWrite):
    # AD v2.2.0 (at least) does not have this. It is present in v1.9.1.
    file_number_sync = None

    def get_frames_per_point(self):
        return self.parent.cam.num_images.get()

    def make_filename(self):
        # stash this so that it is available on resume
        self._ret = super().make_filename()
        return self._ret


class FCCDCam(AreaDetectorCam):
    sdk_version = Cpt(EpicsSignalRO, 'SDKVersion_RBV')
    firmware_version = Cpt(EpicsSignalRO, 'FirmwareVersion_RBV')
    overscan_cols = Cpt(EpicsSignalWithRBV, 'OverscanCols')
    fcric_gain = Cpt(EpicsSignalWithRBV, 'FCRICGain')
    fcric_clamp = Cpt(EpicsSignalWithRBV, 'FCRICClamp')
    temp = FCpt(EpicsSignal, '{self._temp_pv}')

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

        # we need to take the detector out of acquire mode
        self._original_vals[self.cam.acquire] = self.cam.acquire.get()
        set_and_wait(self.cam.acquire, 0)
        # but then watch for when detector state
        while self.cam.detector_state.get(as_string=True) != 'Idle':
            ttime.sleep(.01)

        return super().stage()


class ProductionCamStandard(SingleTrigger, ProductionCamBase):
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
        set_and_wait(self.hdf5.capture, set_val)
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
        # can add this if we're not confident about setting...
        # val = self.hdf5.capture.get()
        # print("resuming FCCD")
        # while (np.abs(val-set_val) > 1e-6):
        # self.hdf5.capture.put(set_val)
        # val = self.hdf5.capture.get()
        # print("Success")
        return super().resume()


class TriggeredCamExposure(Device):
    def __init__(self, *args, **kwargs):
        self._Tc = 0.004
        self._To = 0.0035
        self._readout = 0.080
        super().__init__(*args, **kwargs)

    def set(self, exp: float, triggerrate: float = 1., trigger_on: bool = True, delaytime: float=1e-3, shuttertime: float=140e-3):
        # Exposure time = 0
        # Cycle time = 1

        if exp[0] is not None:
            Efccd = exp[0] + self._Tc + self._To
            # To = start of FastCCD Exposure
            tr = triggerrate  # trigger rate
            tm = trigger_on  # Shutter open
            dt = delaytime  # delay time
            st = shuttertime# shutter time

            # Setup delay generator
            self.parent.dg1.init.set(1)
            self.parent.dg1.trigger_rate.set(tr)
            self.parent.dg1.trigger_on_off.set(tm)
            self.parent.dg1.delay_time.set(dt)
            self.parent.dg1.shutter_time.set(st)

            # self.parent.dg2.A.set(0)
            # self.parent.dg2.B.set(0.0005)

            # Set AreaDetector
            self.parent.cam.acquire_time.set(Efccd)

        # Now do period
        if exp[1] is not None:
            if exp[1] < (Efccd + self._readout):
                p = Efccd + self._readout
            else:
                p = exp[1]

        self.parent.cam.acquire_period.set(p)

        if exp[2] is not None:
            self.parent.cam.num_images.set(exp[2])

        return NullStatus()

    def get(self):
        return None


class DelayGenerator(Device):
    trigger_rate = Cpt(EpicsSignalWithRBV, '.trigger_rate')
    trigger_on_off = Cpt(EpicsSignalWithRBV, '.trigger_on_off')
    delay_time = Cpt(EpicsSignalWithRBV, '.delay_time')
    shutter_time = Cpt(EpicsSignalWithRBV, '.shutter_time')
    init = Cpt(EpicsSignal, '.initialize')
    reset = Cpt(EpicsSignal, '.reset')


# class DelayGeneratorChan(EpicsSignal):
#     def __init__(self, prefix, **kwargs):
#         super().__init__(prefix + '-RB', write_pv=prefix + '-SP', **kwargs)

class ProductionCamTriggered(ProductionCamStandard):
    dg2 = FCpt(DelayGenerator, '{self._dg2_prefix}')
    dg1 = FCpt(DelayGenerator, '{self._dg1_prefix}')
    exposure = Cpt(TriggeredCamExposure, '')
    #TODO: add delay generator code here see areadetector.py
    # https://github.com/NSLS-II-CSX/xf23id1_profiles/blob/master/profile_collection/startup/csx1/devices/areadetector.py
    # line 258
    # scaler/delaygen? defined in
    # https://github.com/NSLS-II-CSX/xf23id1_profiles/blob/master/profile_collection/startup/csx1/devices/scaler.py
    # or
    # https://github.com/NSLS-II-CSX/xf23id1_profiles/blob/master/profile_collection/startup/csx1/devices/devices.py#L134



class StageOnFirstTrigger(ProductionCamTriggered):
    _default_read_attrs = ['hdf5']

    def __init__(self, *args, **kwargs):
        super(StageOnFirstTrigger, self).__init__(*args, **kwargs)
        self._warmed_up = False
        self.trigger_staged = False

    def _trigger_stage(self):
        if not self._warmed_up:
            self.hdf5.warmup()
            self._warmed_up = True
        self._acquisition_signal.subscribe(self._acquire_changed)
        return super(StageOnFirstTrigger, self).stage()

    def stage(self):
        return [self]

    def unstage(self):
        super(StageOnFirstTrigger, self).unstage()
        self._acquisition_signal.clear_sub(self._acquire_changed)
        self.trigger_staged = False

    def trigger(self):

        if not self.trigger_staged:
            self._trigger_stage()
            self.trigger_staged = True

        return super().trigger()

FastCCD = StageOnFirstTrigger
