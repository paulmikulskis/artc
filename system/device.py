'''
This file seeks to organize all the types of device that we might end 
up using to build the bitcoin heater system

GPIO pin numbering scheme is assumed to be the same as the BCM numbering, with
triple digit ranges representing MCP-3008 expansion ICs and 
quadruple digit ranges representing MCP-23017 expansion GPIOs

for example:
    GPIO pin 0 on the first MCP-3008 we have would be pin 100
    GPIO pin 3 on the first MCP-3008 we have would be pin 103
    GPIO pin 3 on the second MCP-3008 we have would be pin 203
    GPIO pin 14 on the first MCP-23017 we have would be pin 1014
    GPIO pin 9 on the second MCP-23017 we have would be pin 2009
'''

from abc import abstractmethod
import time
import RPi.GPIO as GPIO
import digitalio
import board
from messages.types import ErrorType, PiError



class Device:
    def __init__(self, name):
        self.name = name


'''
Class template for registering devices which have a binary state via the GPIO pins, that is,
they are either ON or OFF

This paradigm will allow GPIO-switched devices to have a default on/off ability, while allowing them
to extend that functionality (i.e. with custom delays or checks) if need be in their own implementations
'''
class AdjustableDigitalDevice(Device):

    def __init__(self, name, starting_state, GPIO_pin: digitalio.DigitalInOut):
        super().__init__(name)
        self.name = name
        self.starting_state = starting_state
        self.pin = GPIO_pin
        self.pin.switch_to_output()
        


    def set_to(self, val):
        try:
            if val == 1 or val == True or val == 'on' or val == 'turn on': 
              self.turn_on()
            elif val == 0 or val == False or val == 'off' or val == 'turn off':  
              self.turn_off()
            print('command executed, pin {} value set to {}'.format(self.pin, val))
            return True
        except Exception as e:
            return PiError(
              ErrorType.INTERNAL_ERROR,
              'unable to set relay {} to {}\n{}'.format(self.name, val, e),
              501
            )

    def switch(self):
        self.pin.value = not self.pin.value

    def turn_on(self):
        print('turning "{}" on'.format(self.name))
        self.pin.value = True

    def turn_off(self):
        print('turning "{}" off'.format(self.name))
        self.pin.value = False



'''
Controls a 220v relay switch connected to a GPIO pin
'''
class RelaySwitch(AdjustableDigitalDevice):

    def __init__(self, name, starting_state, GPIO_pin):
        super().__init__(name, starting_state, GPIO_pin)
        self.name = name
        self.starting_state = starting_state
        self.pin = GPIO_pin
