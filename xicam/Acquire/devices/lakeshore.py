from ophyd import Component as Cpt, Device
from ophyd.signal import (EpicsSignalRO, EpicsSignal)
from ophyd.areadetector.base import EpicsSignalWithRBV


class LakeShore336(Device):
    temp_celsius = Cpt(EpicsSignalRO, 'TemperatureCelsius', name='Temperature (°C)')
    temp_kelvin = Cpt(EpicsSignalRO, 'TemperatureKelvin', name='Temperature (°K)')
    heater_output = Cpt(EpicsSignalRO, 'HeaterOutput', name='Heater Output')
    temp_limit = Cpt(EpicsSignalWithRBV, 'TemperatureLimit', name='Temperature Limit (°K)')
    temp_set_point = Cpt(EpicsSignalWithRBV, 'TemperatureSetPoint', name='Temperature Setpoint (°C)')
