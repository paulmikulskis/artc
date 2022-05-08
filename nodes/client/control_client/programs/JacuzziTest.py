import json
from logging import Logger
from typing import List, Tuple
from irc.client import ServerConnection, Event
from client.control_client.control_program_base import ProgramFunctionBase
from client.control_client.control_program_base import Program
from client.miner_client.braiins_asic_client import f
from client.control_client.error import ControlError

FIELD_SEPRATATOR = '::'

class JacuzziTest(ProgramFunctionBase):

    def __init__(self, target_temp=104):
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
        miner = self.last_events('miner')

        
        if stats == None:      
            msg = ' !! No "stats in history'
            log.warn(msg)
            return (None, ControlError(msg, 500, None))
        if miner == None:
            msg = ' !! No "miner" in history'
            log.warn(msg)
            return (None, ControlError(msg, 500, None))

        stats = stats.message()
        stats = stats.split('::', 1)
        miner = miner.message()
        miner = miner.split('::', 1)
        
        if len(stats) < 2 or len(miner) < 2:
            msg = ' !! not enough messag history to run program'
            log.warn(msg)
            return (None, ControlError(msg, 500, None))
        stats = stats[1]
        miner = miner[1]
        if not isinstance(stats, dict):
            try:
                stats = json.loads(stats)
            except:
                msg = ' !! unable to decode stats json'
                log.warn(msg)
                return (None, ControlError(msg, 500, None))
        if not isinstance(miner, dict):
            try:
                miner = json.loads(miner)
            except:
                msg = ' !! unable to decode miner json'
                log.warn(msg)
                return (None, ControlError(msg, 500, None))

        if len(self.return_history) == 0:
            context['phase'] = 'rest'
            log.info('setting program phase to "rest"')

        pump_oil = stats.get('pump_oil')
        pump_water = stats.get('pump_water')
        therm_oil = stats.get('therm_oil')
        therm_water = stats.get('therm_water')
        miner_max_temp = None

        # expecting: {"antminer": {"board_6": {"board": 45}}}
        try:
            miner_max_temp = max([f(m.get('board')) or 0 for _, v in miner.items() for l, m in v.items() if 'board' in l])
        except:
            msg = 'unable to get miner_max_temp maximum: {}'.format(miner_max_temp)
            log.error(msg)
            return (None, ControlError(msg, 500, None))

        if (pump_oil == None) or (pump_water == None) or (therm_oil == None) or (therm_water == None) or (miner_max_temp == None):
            msg = 'unable to get needed stats: {}'.format([pump_oil, pump_water, therm_oil, therm_water])
            log.error(msg)
            return (None, ControlError(msg, 500, None))

        pump_oil = bool(pump_oil)
        pump_water = bool(pump_water)
        therm_oil = float(therm_oil)
        therm_water = float(therm_water)


        if context['phase'] == 'rest':
            if therm_water < self.target_temp:
                if not pump_oil:    connection.privmsg(event.target_string(), 'cmd::chng::pump_oil,on')
                if not pump_water:  connection.privmsg(event.target_string(), 'cmd::chng::pump_water,on')
                if not pump_oil and not pump_water: connection.privmsg(event.target_string(), 'cmd::func::miner::start')
                self.set_phase_to('heating')
                return (True, None)
            if therm_water > self.target_temp:
                if pump_oil:    connection.privmsg(event.target_string(), 'cmd::chng::pump_oil,off')
                if pump_water:  connection.privmsg(event.target_string(), 'cmd::chng::pump_water,off')
                #if not pump_oil and not pump_water: connection.privmsg(event.target_string(), 'cmd::func::miner::stop')
                return (True, None)
            
        if context['phase'] == 'heating':
            if therm_water < self.target_temp + 1:
                if not pump_oil:    connection.privmsg(event.target_string(), 'cmd::chng::pump_oil,on')
                if not pump_water:  connection.privmsg(event.target_string(), 'cmd::chng::pump_water,on')
                if not pump_oil and not pump_water: connection.privmsg(event.target_string(), 'cmd::func::miner::start')
                return (True, None)
            if therm_water > self.target_temp:
                if pump_oil:    connection.privmsg(event.target_string(), 'cmd::chng::pump_oil,off')
                if pump_water:  connection.privmsg(event.target_string(), 'cmd::chng::pump_water,off')
                connection.privmsg(event.target_string(), 'cmd::func::miner::stop')
                self.set_phase_to('rest')
                return (True, None)
            