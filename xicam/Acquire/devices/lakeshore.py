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
    temp_celsius = Cpt(EpicsSignalRO, 'TemperatureCelsius', name='Temperature (°C)')
    temp_kelvin = Cpt(EpicsSignalRO, 'TemperatureKelvin', name='Temperature (°K)')
    heater_output = Cpt(EpicsSignalRO, 'HeaterOutput', name='Heater Output (%)')

    # read-write components (PVs)
    temp_limit = Cpt(EpicsSignalWithRBV, 'TemperatureLimit', name='Temperature Limit (°K)')
    temp_set_point = Cpt(EpicsSignalWithRBV, 'TemperatureSetPoint', name='Temperature Setpoint (°C)')
