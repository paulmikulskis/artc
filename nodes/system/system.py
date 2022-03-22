
'''
Dictionary of all the device and sensor types on the system
'''
import functools
from system.device import RelaySwitch, HallEffectFlowSensor, OneWireThermister
from digitalio import DigitalInOut, Direction
import board

# set the hardware addresses of any thermistors used here
THERMISTOR_ADDRESSES = {
    1: '3c9bf648ac5d',
    2: '3c57f64872a8',
    3: '3c95f648bddd',
    4: '3c4bf6486f79',
    5: '3c5bf6482baa'
}

# list out the devices used in the project
# each device should have a name, and be mapped to an object
# that extends device.Device
device_map = {
    'pump1': RelaySwitch('pump1', False, DigitalInOut(board.D21)),
    'flow1': HallEffectFlowSensor('flow1', 12),
    'therm1': OneWireThermister('therm1', 1, THERMISTOR_ADDRESSES)
}

# list out all the stats to be collected and shipped
# off to InfluxDB
stat_map = {
    'hall1': device_map['flow1'].get_rate,
    'pump1': device_map['pump1'].get_state,
    'therm1': device_map['therm1'].read_farenheight
}