
'''
Dictionary of all the device and sensor types on the system
'''
import functools
from system.device import RelaySwitch, HallEffectFlowSensor, OneWireThermister
from digitalio import DigitalInOut, Direction
import board

ONE_WIRE_ADDRESSES = {
    1: '3c9bf648ac5d',
    2: '3c57f64872a8',
    3: '3c95f648bddd',
    4: '3c4bf6486f79',
    5: '3c5bf6482baa'
}

device_map = {
    'pump1': RelaySwitch('pump1', False, DigitalInOut(board.D21)),
    'flow1': HallEffectFlowSensor('flow1', 12),
    'therm1': OneWireThermister('therm1', 1, ONE_WIRE_ADDRESSES)
}
