from ophyd import Component as Cpt, Device
from ophyd.signal import (EpicsSignalRO, EpicsSignal)
from ophyd.areadetector.base import EpicsSignalWithRBV


class LakeShore336(Device):
    temp_celsius = Cpt(EpicsSignalRO, 'TemperatureCelsius')
    temp_kelvin = Cpt(EpicsSignalRO, 'TemperatureKelvin')
    heater_output = Cpt(EpicsSignalRO, 'HeaterOutput')
    temp_limit = Cpt(EpicsSignalWithRBV, 'TemperatureLimit')
    temp_set_point = Cpt(EpicsSignalWithRBV, 'TemperatureSetPoint')
