from messages.types import ErrorType, PiError
from system.system import device_map

def executeChangeCommand(device_name, newValue, speed=None):
    device = device_map.get(device_name)
    if not device:
        return PiError(
          ErrorType.NO_DEVICE,
          'device {} not found'.format(device_name),
          404
        )
    return device.set_to(newValue)

    
