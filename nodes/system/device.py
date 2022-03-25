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
from datetime import datetime, timedelta
import sys
from typing import List                      # Import sys module
import RPi.GPIO as GPIO
import digitalio
import board
from messages.types import ErrorType, PiError
from client.miner_client.braiins_asic_client import BraiinsOsClient
from w1thermsensor import W1ThermSensor, Sensor, Unit



class Device:
    def __init__(self, name):
        self.name = name


class SystemMiners(Device):

    def __init__(self, hostnames: List[str] or str, name='miners', port=4028, timeout=10, password='1234count'):
        super().__init__(name)
        self.client = BraiinsOsClient(hostnames, port=port, timeout=10, password=password)

    def start_mining(self, hostnames: List[str] or str):
        self.client.start_miner(hostnames)
    
    def stop_mining(self, hostnames: List[str] or str):
        self.client.stop_miner(hostnames)

    def process_command(self, command, hostnames):
        if command == 'stop' or command == 'stop_mining' or command == 'false' or command == False or command == 0:
            self.stop_mining(hostnames)
        if command == 'start' or command == 'start_mining' or command == 'true' or command == True or command == 1:
            self.start_mining(hostnames)


'''
Class template for registering devices which have a binary state via the GPIO pins, that is,
they are either ON or OFF

This paradigm will allow GPIO-switched devices to have a default on/off ability, while allowing them
to extend that functionality (i.e. with custom delays or checks) if need be in their own implementations
'''
class AdjustableDigitalDevice(Device):

    def __init__(self, name, starting_state, GPIO_pin):
        super().__init__(name)
        self.name = name
        self.starting_state = starting_state
        self.pin = GPIO_pin
        self.pin.switch_to_output()
        self.pin.value = starting_state
        

    def set_to(self, val):
        try:
            if val == 1 or val == True or val == 'on' or val == 'turn on': 
              self.turn_on()
            elif val == 0 or val == False or val == 'off' or val == 'turn off':  
              self.turn_off()
            print('command executed, pin {} value set to {}'.format(self.pin._pin, val))
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

    def get_state(self):
        return self.pin.value



'''
Monitors the temperature readings of a OneWire-based thermister
'''
class OneWireThermister(Device):

    def __init__(self, name, id, ONE_WIRE_ADDRESSES, factory_id=None, sensor_type=Sensor.DS18B20):
        super().__init__(name)
        self.sensor_type = sensor_type
        self.id = id
        self.factory_id=factory_id
        self.address_map = ONE_WIRE_ADDRESSES
        self.sensor = W1ThermSensor(sensor_type=self.sensor_type, sensor_id=self.address_map[self.id])

    def read_farenheight(self):
        return self.sensor.get_temperature(Unit.DEGREES_F)

    def read_celsius(self):
        return self.sensor.get_temperature()


'''
Controls a 220v relay switch connected to a GPIO pin
'''
class RelaySwitch(AdjustableDigitalDevice):

    def __init__(self, name, starting_state, GPIO_pin):
        super().__init__(name, starting_state, GPIO_pin)
        self.name = name
        self.starting_state = starting_state
        self.pin = GPIO_pin


'''
Monitors the input with lookback history for a HallEffect sensor
'''
class HallEffectFlowSensor:

    def __init__(self, name, input_pin, deltaT=10, history=100):
        self.name = name
        self.input_pin = input_pin
        GPIO.setup(input_pin, GPIO.IN)

        self.delta_revs = [-1 for i in range(history)]
        self.current_delta_revs = 0
        self.last_time = datetime.now()
        self.constant = 0.1
        self.rate = 0
        self.deltaT = deltaT

    # channel is required by the RPi.GPIO library, but we make it optional
    # to allow for intentional calls to detect() for RealTime measurements
    def detect(self, channel=None):
        tim = datetime.now()
        fast_read = (channel is None) and ((tim - self.last_time).seconds > (self.deltaT / 2))
        if (tim - self.last_time > timedelta(seconds=self.deltaT)) or fast_read:
            self.delta_revs.append(self.current_delta_revs)
            self.delta_revs.pop(0)
            self.current_delta_revs = 0
            self.last_time = tim

        if channel is not None:
          self.current_delta_revs += 1

    
    def listen(self):
        GPIO.add_event_detect(self.input_pin, GPIO.BOTH, callback=self.detect, bouncetime=20)


    def stop(self):
        GPIO.remove_event_detect(self.input_pin)

    
    def get_rate(self, lookback=timedelta(seconds=10)):
        now = datetime.now()
        lookback_indices = int(lookback.seconds / self.deltaT) or 1
        if lookback_indices > len(self.delta_revs):
            lookback_indices = len(self.delta_revs)

        selected = self.delta_revs[-1]
        for i in range(int((now - self.last_time).seconds / self.deltaT)):
            self.delta_revs.append(selected)
            self.delta_revs.pop(0)

        self.detect()
        selected = self.delta_revs[len(self.delta_revs) - lookback_indices:]

        return round((sum(selected) / len(selected)) * self.constant, 4)