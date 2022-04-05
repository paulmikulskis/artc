
'''
Dictionary of all the device and sensor types on the system
'''
import functools
from typing import Dict
from client.miner_client.braiins_asic_client import BraiinsOsClient
from system.device import SystemMiners
from system.device import Device
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
device_map: Dict[str, Device] = {
    'pump_oil': RelaySwitch('pump_oil', False, DigitalInOut(board.D26)),
    'pump_water': RelaySwitch('pump_water', False, DigitalInOut(board.D19)),
    'therm_oil': OneWireThermister('therm_oil', 1, THERMISTOR_ADDRESSES),
    'therm_water': OneWireThermister('therm_water', 2, THERMISTOR_ADDRESSES),
    'miners': SystemMiners('antminer')
}

# list out all the stats to be collected and shipped
# off to InfluxDB
stat_map = {
    'pump_oil': device_map['pump_oil'].get_state,
    'pump_water': device_map['pump_water'].get_state,
    'therm_oil': device_map['therm_oil'].read_farenheight,
    'therm_water': device_map['therm_water'].read_farenheight,
    'miners': device_map['miners'].get_temps
}