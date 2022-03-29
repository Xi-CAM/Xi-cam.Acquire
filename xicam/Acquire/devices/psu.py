from ophyd import Component as Cpt, Device
from ophyd.signal import (EpicsSignalRO, EpicsSignal)
from ophyd.areadetector.base import EpicsSignalWithRBV


class PSUChannel(Device):
    voltage = Cpt(EpicsSignalRO, 'Voltage', name='Voltage')
    current = Cpt(EpicsSignalRO, 'Current', name='Current')


class BiasClocksPSU(Device):
    channel0 = Cpt(PSUChannel, 'Out1:')
    channel1 = Cpt(PSUChannel, 'Out2:')
    channel2 = Cpt(PSUChannel, 'Out3:')
    channel3 = Cpt(PSUChannel, 'Out4:')


class FCRICFOPSPSU(Device):
    channel0 = Cpt(PSUChannel, 'Out1:')
    channel1 = Cpt(PSUChannel, 'Out2:')


class PSU(Device):
    """

    """

    bias_clocks_psu = Cpt(BiasClocksPSU, 'BiasClocksPSU:')
    fcric_fops_psu = Cpt(FCRICFOPSPSU, 'FCRICFOPSPSU:')

    state = Cpt(EpicsSignal, 'State')

    # putting to these trigger these states
    on = Cpt(EpicsSignal, 'On')
    off = Cpt(EpicsSignal, 'Off')
