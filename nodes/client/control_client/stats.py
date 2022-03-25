from enum import Enum
import json
from typing import Dict, List
from irc.client import Connection

# All functions should take in a:
#   'message' parameter, being the string-encoded JSON from the system_client
#   'connection' parameter being the IRC Client Connection class
#    
#    the program can then send back messages with connection.privmg(target, msg)
def hand_test(message: str, connection: Connection) -> List[bool]:
    '''
    First program made for the bitcoin heating experiment.  THe goal of this test
    is to show a proper connection and messaging path between all the connected components.

    There should be two temperature sensors, a pump, a flow sensor, and a bitcoin miner
    if the activation temperature sensor gets over a threshold like 75F (so it can be induced by grasping in your hand),
    the miner will turn on.  Once the second temperature sensor gets over another similar threshold, the miner will stop
    and the pump will turn on, displaying positive flow through the sensor.  
    '''
    try:
        message = json.loads(message)
    except Exception as e:
        return [False]
    


class Program:

    def __init__(self, functions: function or List[function], deployment_ids: List[str]=None, name:str='default', ):
        self.name = name
        self.functions = functions if isinstance(functions, list) else [functions]
        self.deployment_ids = deployment_ids


class StatProcessors:

    def __init__(
        self, 
        deployment_ids: List[str] or str,
        programs: List[Program] or Program,
    ):
        self.deployment_ids = deployment_ids if isinstance(deployment_ids, list) else [deployment_ids]
        self.programs = programs if isinstance(Program, list) else [programs]


    def process(self, message: str, target: str, connection: Connection ):
        results_map = {}
        for program in self.programs:
            if target is None or target in program.deployment_ids:
                results_map[program.name] = list(map(lambda x: x(message, connection), program.functions))
            else: results_map[program.name] = [False]
        return results_map
        


