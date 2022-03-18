
'''
Dictionary of all the device and sensor types on the system
'''
from system.device import RelaySwitch


device_map = {
    'pump1_relay': RelaySwitch('pump1', False, 21),
}