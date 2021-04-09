from ophyd import Component as Cpt, Device
from ophyd.signal import (EpicsSignalRO, EpicsSignal)


class DetectorDiode(Device):
    diode = Cpt(EpicsSignalRO, '.VAL', name = 'Diode Current')

    _default_read_attrs = ['diode']
