from enum import Enum
import json
from logging import Logger
import logging
import os
from posixpath import abspath, dirname, join
from typing import Dict, List
from dotenv import load_dotenv
from irc.client import ServerConnection, Event
from client.control_client.control_program_base import Program, ProgramFunctionBase


class MessageProcessor:

    def __init__(
        self, 
        deployment_ids: List[str] or str,
        programs: List[Program] or Program or None = None,
    ):
        self.deployment_ids = deployment_ids if isinstance(deployment_ids, list) else [deployment_ids]
        if programs is not None:
            self.programs = programs if isinstance(programs, list) else [programs]
        else:
            self.programs = []
        
        BASEDIR = abspath(dirname(__file__))
        load_dotenv(join(BASEDIR, '../../../.base.env'))
        log_level = os.environ.get("LOG_LEVEL")
        if log_level not in list(map(lambda x: x[1], logging._levelToName.items())):
            log_level = 'INFO'
        log_type = os.environ.get("LOG_TYPE")
        if log_type not in ['FULL', 'CLEAN']:
            log_type = 'FULL'


        ch = logging.StreamHandler()
        log = logging.getLogger(__name__.split('.')[-1])

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') if log_type == 'FULL' else logging.Formatter('%(name)s - %(message)s')
        ch.setFormatter(formatter)
        log.addHandler(ch)
        log.setLevel(log_level)
        self.logger = log


    def process(self, connection: ServerConnection, event: Event ):
        if (event.target == '#control') or (event.target == '#control_bot') or (event.target[1:] == connection.nickname):
            return self.intake_command(connection, event)
        else:
            return self.process_node_message(connection, event)
 

    def intake_command(self, connection: ServerConnection, event: Event):
        message = event.message()
        parts = message.split('::')
        if len(parts) < 2:
            self.logger.error('unable to intake_command: "{}"'.format(message))
            return False
        switch = parts[0]
        # only accepting 'cmd' messages at this time
        if switch != 'cmd':
            self.logger.error('unable to intake_command: "{}"'.format(message))
            return [False]

        if len(parts) < 3:
            self.logger.error('unable to intake_command, no third piece: "{}"'.format(message))
            return [False]

        command = parts[1]
        args = parts[2].split(',')
        args: List[Program] = list(filter(lambda x: x.name in args, self.programs))

        if command == 'start':
            connection.privmsg(event.target, 'starting programs "{}"'.format(args))
            return [self.start_processing(arg) for arg in args]
        if command == 'stop':
            connection.privmsg(event.target, 'stopping programs "{}"'.format(args))
            return [self.stop_processing(arg.name) for arg in args]
        
        self.logger.error('command "{}" not implemented yet...  arguments: {}'.format(command, args))
        return [False]


    def process_node_message(self, connection: ServerConnection, event: Event):
        target = event.target
        if target[0] == '#':
            target = target[1:]
        results_map = {}
        for program in self.programs:
            program_name = program.active_function().__class__.__name__
            if ((self.deployment_ids) is None ) or (target in self.deployment_ids):
                results_map[program_name] = program.run(connection, event)
            else: results_map[program_name] = [False]
            self.logger.info('finished running this MessageProcessor\'s programs: {}'.format(list(map(lambda x: x.name, self.programs))))
            self.logger.debug('  results_map:  {}'.format(results_map))

        return results_map


    def start_processing(self, program: Program):
        '''
        Adds a Program to this MessageProcessor, as long as no other program with this name exists
        '''
        name = program.name
        if name not in list(map(lambda x: x.name, self.programs)):
            self.programs.append(program)
            return True
        else:
            self.logger.error('cannot add program {} to this MessageProcessor, name taken.'.format(name))
            return False


    def stop_processing(self, name: str):
        '''
        Tells this MessageProcessor to stop running the program with name 'name'
        '''
        try:
            index = list(map(lambda x: x.name, self.programs)).index(name)
            return True
        except ValueError:
            self.logger.error('cannot remove program {} to this MessageProcessor, name not found.'.format(name))
            return False

        


