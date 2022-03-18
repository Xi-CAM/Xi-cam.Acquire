from ophyd import Component as Cpt, Device
from ophyd.signal import (EpicsSignalRO, EpicsSignal)
from ophyd.areadetector.base import EpicsSignalWithRBV


class LakeShore336(Device):
    """
    Ophyd Device for the Lakeshore 336 temperature controller
    https://www.lakeshore.com/docs/default-source/product-downloads/336_manual.pdf?sfvrsn=fa4e3a80_5
    based on lakeshore336_ioc
    https://github.com/lbl-camera/fastccd_support_ioc/blob/lakeshore336/fastccd_support_ioc/lakeshore336_ioc.py
    """
    # read-only components (PVs)
    temp_celsius_A = Cpt(EpicsSignalRO, 'TemperatureCelsiusA', name='Temperature (°C)')
    temp_kelvin_A = Cpt(EpicsSignalRO, 'TemperatureKelvinA', name='Temperature (°K)')
    temp_celsius_B = Cpt(EpicsSignalRO, 'TemperatureCelsiusB', name='Temperature (°C)')
    temp_kelvin_B = Cpt(EpicsSignalRO, 'TemperatureKelvinB', name='Temperature (°K)')
    heater_output = Cpt(EpicsSignalRO, 'HeaterOutput', name='Heater Output (%)')

    # read-write components (PVs)
    temp_limit_A = Cpt(EpicsSignalWithRBV, 'TemperatureLimitA', name='Temperature Limit (°K)')
    temp_limit_B = Cpt(EpicsSignalWithRBV, 'TemperatureLimitB', name='Temperature Limit (°K)')
    temp_set_point = Cpt(EpicsSignalWithRBV, 'TemperatureSetPoint', name='Temperature Setpoint (°C)')
