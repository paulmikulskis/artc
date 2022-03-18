
'''
Dictionary of all the device and sensor types on the system
'''
from system.device import RelaySwitch, HallEffectFlowSensor
from digitalio import DigitalInOut, Direction
import board

device_map = {
    'pump1': RelaySwitch('pump1', False, DigitalInOut(board.D21)),
    'flow1': HallEffectFlowSensor('flow1', 12)
}