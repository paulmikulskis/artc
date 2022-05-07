from enum import Enum
import json
from logging import Logger
import logging
import os
from posixpath import abspath, dirname, join
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from irc.client import ServerConnection, Event
from client.control_client.control_program_base import Program

# import and list all programs here:
from client.control_client.programs.HandOnOffTest import HandOnOffTest
from client.control_client.programs.JacuzziTest import JacuzziTest

ALL_PROGRAMS = [
    HandOnOffTest,
    JacuzziTest
]

class ControlError:

    def __init__(self, msg: str, code: int, e: Exception or None):
        self.msg = msg
        self.code = code
        self.exception = e

    def __str__(self):
        return '{}: {}\nexception: {}'.format(self.code, self.msg, self.exception)

class MessageProcessor:

    def __init__(
        self, 
        deployment_dict
    ):
        self.deployments: dict = deployment_dict
        
        BASEDIR = abspath(dirname(__file__))
        load_dotenv(join(BASEDIR, '../../../.base.env'))
        log_level = os.environ.get("LOG_LEVEL")
        if log_level not in list(map(lambda x: x[1], logging._levelToName.items())):
            log_level = 'INFO'
        log_type = os.environ.get("LOG_TYPE")
        if log_type not in ['FULL', 'CLEAN']:
            log_type = 'FULL'


        ch = logging.StreamHandler()
        # log = logging.getLogger(__name__.split('.')[-1])
        log = logging.getLogger('control_runner')

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') if log_type == 'FULL' else logging.Formatter('%(name)s - %(message)s')
        ch.setFormatter(formatter)
        log.addHandler(ch)
        log.setLevel(log_level)
        self.logger = log


    def process(self, connection: ServerConnection, event: Event ) -> Tuple[bool or None, ControlError or None]:
        target = event.target_string()
        if len(target) < 2:
            msg = 'unable to process_node_message, unable to parse IRC event target: "{}"'.format(target)
            return (None, ControlError(msg, 500, None))
        if target[0] == '#':
            target = target[1:]
        if target not in list(self.deployments.keys()):
            msg = 'unable to process_node_message, deployment "{}" is not registered to this processor'.format(target)
            return (None, ControlError(msg, 500, None))

        if (event.message().split('::')[::-1].pop() == 'control') or (event.message().split('::')[::-1].pop() == 'control_bot'):
            self.logger.info('intaking command message from {}'.format(event.source_string()))
            return self.intake_command(connection, event)
        else:
            if len(list(self.deployments.keys)) == 0:
                msg = 'skip processing, no deployments configured!'
                self.logger.info(msg)
                return [None, ControlError(msg, 500, None)]
            self.logger.info('processing message from {}'.format(event.source_string()))
            return self.process_node_message(connection, event)
            
 

    def intake_command(self, connection: ServerConnection, event: Event) -> Tuple[bool or None, ControlError or None]:
        message = event.message()
        parts = message.split('::')
        if len(parts) < 2:
            msg = 'unable to intake_command: "{}"'.format(message)
            self.logger.error(msg)
            return (None, ControlError(msg, 500, None))
        switch = parts[0]
        # only accepting 'cmd' messages at this time
        if switch != 'control':
            msg = 'unable to intake_command: "{}", only accepting "control"'.format(message)
            self.logger.error(msg)
            return (None, ControlError(msg, 500, None))

        if len(parts) < 3:
            msg = 'unable to intake_command, no third piece: "{}"'.format(message)
            self.logger.error(msg)
            return (None, ControlError(msg, 500, None))

        command = parts[1]
        args = parts[2].split(',')
        # args = [ProgramName, param1, param2]
        program_name = args[0]
        program = list(filter(lambda x: str(x().__class__.__name__).lower() == program_name, ALL_PROGRAMS)).pop()
        if not program:
            msg = 'unable to process_node_message, unable to find program: "{}"'.format(program_name)
            return (None, ControlError(msg, 500, None))

        target = event.target_string()
        if len(target) < 2:
            msg = 'unable to process_node_message, unable to parse IRC event target: "{}"'.format(target)
            return (None, ControlError(msg, 500, None))
        if target[0] == '#':
            target = target[1:]
        if target not in list(self.deployments.keys()):
            msg = 'unable to process_node_message, deployment "{}" is not registered to this processor'.format(target)
            return (None, ControlError(msg, 500, None))

        if command == 'start':
            connection.privmsg(event.target, 'starting programs "{}"'.format(args))
            new_program = Program(program(*args[1:]))
            return self.start_processing(new_program, target, event)
        if command == 'stop':
            connection.privmsg(event.target, 'stopping programs "{}"'.format(args))
            return self.stop_processing(program_name, target)
        
        msg = '"{}" not implemented yet...  arguments: {}'.format(command, args)
        self.logger.error(msg)
        return (None, ControlError(msg, 500, None))


    def process_node_message(self, connection: ServerConnection, target: str, event) -> Tuple[bool or None, ControlError or None]:
        
        program = self.deployments.get(target)
        if not program:
            msg = 'unable to process_node_message, deployment "{}" has no active program'.format(target)
            return (None, ControlError(msg, 500, None))
        
        program_name = program.active_function.__class__.__name__
        result = program.run(connection, event)
        self.logger.info('finished running program "{}", result: {}'.format(program_name, result))
        return result


    def start_processing(self, program: Program, target: str, event: Event) -> Tuple[bool or None, ControlError or None]:
        '''
        Adds a Program to this MessageProcessor, as long as the deployment ID can be found and the program exists
        '''
        
        name = program.name
        self.logger.info('attempting to add program "{}"'.format(name))
        self.deployments[target] = program
        return [True, None]


    def stop_processing(self, program_name: str, target: str) -> Tuple[bool or None, ControlError or None]:
        '''
        Tells this MessageProcessor to stop running the program with name 'name'
        '''
        self.logger.info('stopping program "{}"'.format(program_name))
        self.deployments[target] = None
        return [True, None]
        


        


