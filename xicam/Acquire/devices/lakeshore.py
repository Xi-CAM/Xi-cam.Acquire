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
    temp_celsius = Cpt(EpicsSignalRO, 'TemperatureCelsius')
    temp_kelvin = Cpt(EpicsSignalRO, 'TemperatureKelvin')
    heater_output = Cpt(EpicsSignalRO, 'HeaterOutput')

    # read-write components (PVs)
    temp_limit = Cpt(EpicsSignalWithRBV, 'TemperatureLimit')
    temp_set_point = Cpt(EpicsSignalWithRBV, 'TemperatureSetPoint')
