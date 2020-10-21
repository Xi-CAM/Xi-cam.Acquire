import ophyd
from typing import Dict, Tuple, List, Callable
import happi


class CompoundDevice(ophyd.Device):
    def __init__(self, prefix='', *, name, client: happi.Client, devices: List[str]):
        super(CompoundDevice, self).__init__(prefix=prefix, name=name)

        self.devices = client.find_device()

    def stage(self) -> List[object]:
        raise NotImplementedError(
            "This compound device cannot be used with Bluesky. Rather, you should use one of the following component devices for acquisition:\n" + '\n'.join(
                self.devices) + '\n')
