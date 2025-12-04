from bluesky.plans import scan, grid_scan, count, rel_scan, list_scan, rel_list_scan, list_grid_scan, \
    rel_list_grid_scan, log_scan, rel_log_scan, scan_nd, spiral, spiral_fermat, spiral_square, rel_spiral, \
    rel_spiral_fermat, rel_spiral_square, adaptive_scan, rel_adaptive_scan, tune_centroid, tweak, ramp_plan, fly
from caproto import CaprotoTimeoutError
from pyqtgraph.parametertree.parameterTypes import SimpleParameter, ListParameter
from xicam.gui.utils import ParameterizablePlan
from xicam.plugins import manager as plugin_manager
from xicam.core import msg
from happi.loader import from_container
from xicam.Acquire.patches import DeviceParameter
from bluesky import plan_stubs


def find_device(**filter):
    """
    Returns the first device matching the provided filter
    """
    happi_devices = plugin_manager.get_plugin_by_name('happi_devices', 'SettingsPlugin')
    try:
        return from_container(happi_devices.search(**filter)[0].item)
    except IndexError:
        msg.logMessage(f'Device not found: {filter}')
    except (CaprotoTimeoutError, TimeoutError):
        msg.logMessage(f'Device not connected: {filter}')


def find_devices(**filter):
    """
    Returns all devices matching the provided filter
    """
    happi_devices = plugin_manager.get_plugin_by_name('happi_devices', 'SettingsPlugin')
    return [from_container(container.item) for container in happi_devices.search(**(filter))]


class plans:
    scan = ParameterizablePlan(scan)
    grid_scan = ParameterizablePlan(grid_scan)
    ...


__all__ = ['plans',
           'SimpleParameter',
           'ListParameter',
           'ParameterizablePlan',
           'DeviceParameter',
           'find_device',
           'find_devices',
           'plan_stubs']
