from typing import List
from messages.types import ErrorType, PiError
from system.device import SystemMiners
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


def executeFunction(function_name, function_params):
    if function_name == None:
        return PiError(
            ErrorType.NO_DEVICE,
            'no function name specified',
            404
          )
    if function_name == 'miners' or function_name == 'miner':
        executeMinerFunction(*function_params)


def executeMinerFunction(command, hosts=None):
    miner_clients: List[SystemMiners] = filter(lambda x: isinstance(x[1], SystemMiners), device_map.items())
    if not miner_clients:
        return PiError(
          ErrorType.NO_DEVICE,
          'no miner clients registered, device names: {}'.format(map(lambda x: x[1].name, device_map.items())),
          404
        )
    return map(lambda x: x.process_command(command, hosts), miner_clients)

    
