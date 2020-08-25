from qtpy.QtWidgets import *
from qtpy.QtCore import *

from xicam.plugins import manager as pluginmanager


class DeviceView:

    def __init__(self):
        super(DeviceView, self).__init__()

        happi_settings_plugin = pluginmanager.get_plugin_by_name('happi_devices',
                                                                 'SettingsPlugin')
        self.view = happi_settings_plugin.devices_view
        self.model = happi_settings_plugin.devices_model
