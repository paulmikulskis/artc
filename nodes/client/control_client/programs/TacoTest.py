import json
from logging import Logger
from typing import List, Tuple
from irc.client import ServerConnection, Event
from client.control_client.control_program_base import ProgramFunctionBase
from client.control_client.control_program_base import Program
from client.miner_client.braiins_asic_client import f
from client.control_client.error import ControlError

FIELD_SEPRATATOR = '::'

class TacoTest(ProgramFunctionBase):

    def __init__(self, target_temp=69):
        try:
            self.target_temp = float(target_temp)
        except:
            print('non float parsable value used to instantiatue JacuzziTest program!  Setting to 0')
            self.target_temp = 0.0

        # optionally setting this Program's current arguments will make these visible to Influx
        self.arguments = {
           'target_temp': self.target_temp
        }


    def set_target_temp(self, target_temp: float or int) -> bool:
        self.target_temp = target_temp
        self.arguments['target_temp'] = target_temp
        return (True, None)


    def run(self) -> Tuple[bool or None, ControlError or None]:
        message: str = self.message
        message_history: List[str] = self.event_history
        return_history: List[any] = self.return_history
        connection: ServerConnection = self.connection
        event: Event = self.event
        context: Program = self.context.context
        log: Logger = self.logger


        parts = message.split(FIELD_SEPRATATOR)
        message_type = parts[0]

        stats = self.last_events('stats')
        # miner = self.last_events('miner')

        
        if stats == None:      
            msg = ' !! No "stats in history'
            log.warn(msg)
            return (None, ControlError(msg, 500, None))
        # if miner == None:
        #     msg = ' !! No "miner" in history'
        #     log.warn(msg)
        #     return (None, ControlError(msg, 500, None))

        stats = stats.message()
        stats = stats.split('::', 1)
        # miner = miner.message()
        # miner = miner.split('::', 1)
        
        if len(stats) < 2:
            msg = ' !! not enough messag history to run program'
            log.warn(msg)
            return (None, ControlError(msg, 500, None))
        stats = stats[1]
        if not isinstance(stats, dict):
            try:
                stats = json.loads(stats)
            except:
                msg = ' !! unable to decode stats json'
                log.warn(msg)
                return (None, ControlError(msg, 500, None))
        
        if len(self.return_history) == 0:
            context['phase'] = 'rest'
            log.info('setting program phase to "rest"')

        therm_oil = stats.get('therm_oil')
        relay = stats.get('relay')

        if (relay == None) or (therm_oil == None):
            msg = 'unable to get needed stats: {}'.format([relay, therm_oil])
            log.error(msg)
            return (None, ControlError(msg, 500, None))

        relay = bool(relay)
        therm_oil = float(therm_oil)

        if context['phase'] == 'rest':
            if therm_oil < self.target_temp:
                if not relay:    connection.privmsg(event.target_string(), 'cmd::chng::relay,on')
                self.set_phase_to('heating')
                return (True, None)
            if therm_oil > self.target_temp:
                if relay:    connection.privmsg(event.target_string(), 'cmd::chng::relay,off')
                return (True, None)
            
        if context['phase'] == 'heating':
            if therm_oil < self.target_temp + 1:
                if not relay:    connection.privmsg(event.target_string(), 'cmd::chng::relay,on')
                return (True, None)
            if therm_oil > self.target_temp:
                if relay:    connection.privmsg(event.target_string(), 'cmd::chng::relay,off')
                self.set_phase_to('rest')
                return (True, None)
            