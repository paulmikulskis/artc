
'''
Dictionary of all the device and sensor types on the system
'''
import functools
from system.device import RelaySwitch, HallEffectFlowSensor
from digitalio import DigitalInOut, Direction
import board

device_map = {
    'pump1': RelaySwitch('pump1', False, DigitalInOut(board.D21)),
    'flow1': HallEffectFlowSensor('flow1', 12)
}

stats_map = {
    'hall1': device_map['flow1'].get_rate,
    'pump1': device_map['pump1'].get_state
}