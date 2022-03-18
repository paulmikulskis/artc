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
import RPi.GPIO as GPIO
from messages.types import ErrorType, PiError

class Device:
    GPIO.setmode(GPIO.BCM)
    def __init__(self, name):
        self.name = name


class AdjustableDevice(Device):

    def __init__(self, name, starting_state):
        super().__init__(name)
        self.name = name
        self.starting_state = starting_state


    @abstractmethod
    def set_to(self, val):
        pass


'''
Controls a 220v relay switch connected to a GPIO pin
'''
class RelaySwitch(AdjustableDevice):

    def __init__(self, name, starting_state, GPIO_pin):
        super().__init__(name, starting_state)
        self.state = starting_state
        self.pin = GPIO_pin

        GPIO.setup(self.pin, GPIO.OUT)

    def set_to(self, val):
      try:
          if val == 1 or val == True or val == 'on' or val == 'turn on': 
            self.turn_on()
          elif val == 0 or val == False or val == 'off' or val == 'turn off':  
            self.turn_off()
          return True
      except Exception as e:
          return PiError(
            ErrorType.INTERNAL_ERROR,
            'unable to set relay {} to {}\n{}'.format(self.name, val, e),
            501
          )

    def turn_on(self):
        GPIO.output(self.pin, 1)

    def turn_off(self):
        GPIO.output(self.pin, 0)

    def switch(self):
        GPIO.output(self.pin, not self.state)

