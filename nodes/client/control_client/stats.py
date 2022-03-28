from enum import Enum
import json
from typing import Dict, List
from irc.client import ServerConnection, Event
from client.control_client.control_program_base import Program, ProgramFunctionBase

FIELD_SEPRATATOR = '::'

class HandOnOffTest(ProgramFunctionBase):

    def run(self) -> bool:
        '''
        Defines the function or 'script' that a Program will call when it is invoked.
        This method is required by the abstract base class, ProgramFunctionBase and 
        provides access to several @properties which refer back to the Program object that 
        this function or 'script' is running in.  

        Having access to the Program object allows you to refer directly to certain state and
        context entities such as self.connection, which will get populated by Program when my_program.run(*args) is called

        The return value can be anything, though it is good practive to keep it small such as a boolean or small string.
        Encoding large JSON objects is not advised because the return value is saved upon every invocation by
        the calling Program (up to a certain amount) to allow for some lookback functionality if needed in business logic.

        Some other methods of interest:
            - self.last_messasges(str, n=1)
                returns the last n messages of type 'type', i.e. 'stats::{"some": 1, "stats": 2.3}' could match 'stats
            - self.target()
                returns the target of the message
            - self.call(ProgramFunctionBase)
                tells the Program to call another function or 'script' moving forward instead of this one
        '''
        
        # Variables made available via the ProgramFunctionBase class
        # message holds the entire text encoded message i.e. 'stats::{"some": 1, "stats": 2.3}'
        message: str = self.message
        # message_history holds the last n messages as configured by this Program base
        message_history: List[str] = self.event_history
        # return history holds the last n return values of this 'run()' function
        return_history: List[any] = self.return_history
        # connections holds the ServerConnection object from the IRC client that is used to
        # send back messages such as connection.notice('my_words')
        connection: ServerConnection = self.connection
        # event holds the Event object from the IRC client that is used to identify some small
        # metadata about the incoming message such as 'event.target' and 'event.source'
        event: Event = self.event
        # context is a back-reference to the holding Program that runs this function, meaning
        # it can be used as a general purpose store for any other variables, as well as
        # provide access to functions in the Program class such as 'call()' to supercede to another function
        context: Program = self.context


        parts = message.split(FIELD_SEPRATATOR)
        message_type = parts[0]

        stats = self.last_events('stats')
        
        if stats == None:
            print(' !! No stats in history')
            return False

        stats = stats.message()
        stats = stats.split('::', 1)
        if len(stats) < 2:
            return False
        stats = stats[1]
        print('{} program got stats.message:\n  {}'.format(self.name, stats))
        try:
            stats = json.loads(stats)
        except:
            print(' !! unable to decode json: {}'.format(stats))
            return False
        if len(self.return_history) == 0:
            context.phase = 'rest'

        hall1 = stats.get('hall1')
        pump1 = stats.get('pump1')
        therm1 = stats.get('therm1')
        therm2 = stats.get('therm2')

        if (hall1 == None) or (pump1 == None) or (therm1 == None) or (therm2 == None):
            print('unable to get needed stats:', [hall1, pump1, therm1, therm2])
            return False

        # System at rest:
        if context.phase == 'rest':
            if float(therm1) > 75.0:
                connection.privmsg(event.source, 'func::miner::start')
                context.phase = 'mine'
                
        # System detects need to produce heat:
        if context.phase == 'mine':
            if float(therm2) > 75.0:
                connection.privmsg(event.source, 'func::miner::stop')
                connection.privmsg(event.source, 'cmd::chng::pump1,on')
                context.phase = 'pump'

        # System pumps new heat until original condition ceases:
        if context.phase == 'pump':
            if float(therm1) < 75:
                connection.privmsg(event.source, 'cmd::chng::pump1,off')
                context.phase = 'rest'



class MessageProcessor:

    def __init__(
        self, 
        deployment_ids: List[str] or str,
        programs: List[Program] or Program,
    ):
        self.deployment_ids = deployment_ids if isinstance(deployment_ids, list) else [deployment_ids]
        self.programs = programs if isinstance(programs, list) else [programs]


    def process(self, connection: ServerConnection, event: Event ):
        target = event.target
        if target[0] == '#':
            target = target[1:]
        results_map = {}
        for program in self.programs:
            program_name = program.active_function().__class__.__name__
            if (self.deployment_ids) is None or (target in self.deployment_ids):
                results_map[program_name] = program.run(connection, event)
            else: results_map[program_name] = [False]
        
        print('finished running this StatProcessor\'s programs: {}'.format(list(map(lambda x: x.name, self.programs))))
        print('  results_map:\n  {}\n---------\n'.format(results_map))
        return results_map
        


