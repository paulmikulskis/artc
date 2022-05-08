from typing import List, Tuple
from messages.types import ErrorType, PiError
from system.device import SystemMiners
from system.system import device_map

def executeChangeCommand(device_name, newValue, speed=None) -> Tuple[any, PiError]:
    device = device_map.get(device_name)
    if not device:
        return (None, PiError(
          ErrorType.NO_DEVICE,
          'device {} not found'.format(device_name),
          404
        ))
    try:
        val = device.set_to(newValue)
        return [val, None]
    except Exception as e:
        return (None, 
            PiError(
            ErrorType.DEVICE_ERROR,
            'error setting {} to {}, {}'.format(device_name, newValue, e)
        ))


def executeFunction(function_name, function_params) -> Tuple[any, PiError]:
    print('executing FUNC message..\n  function_name: {}\n  params: {}'.format(function_name, function_params))
    if function_name == None:
        return (None, PiError(
            ErrorType.NO_DEVICE,
            'no function name specified',
            404
          ))
    if function_name == 'miners' or function_name == 'miner':
        return executeMinerFunction(*function_params)


def executeMinerFunction(command, hosts=[]) -> Tuple[any, PiError]:
    miner_clients: List[SystemMiners] = list(map(lambda y: y[1], filter(lambda x: isinstance(x[1], SystemMiners), device_map.items())))
    print('  executing Miner Function...')
    print('  clients to address: {}'.format(miner_clients))
    if not miner_clients:
        return (None, PiError(
          ErrorType.NO_DEVICE,
          'no miner clients registered, device names: {}'.format(list(map(lambda x: x[0], device_map.items()))),
          404
        ))
    print('about to execute {} on {}'.format(command, hosts))
    resp = list(map(lambda x: x.process_command(command, hosts), miner_clients))
    error = list(filter(lambda x: x[1] is not None, resp)).pop()
    if error:
        return (None, error)
    return (resp, None)


    
