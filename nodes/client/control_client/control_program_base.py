from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty
import logging
import os
from posixpath import abspath, dirname, join
from re import L
from dotenv import load_dotenv
from irc.client import ServerConnection, Event
import sys
from typing import List

# Get the path to the directory this file is in
BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../../../.base.env'))
log_level = os.environ.get("LOG_LEVEL")
log_type = os.environ.get("LOG_TYPE")

if log_level not in list(map(lambda x: x[1], logging._levelToName.items())):
    log_level = 'INFO'
if log_type not in ['FULL', 'CLEAN']:
    log_type = 'FULL'

ch = logging.StreamHandler()
log = logging.getLogger(__name__.split('.')[-1])

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') if log_type == 'FULL' else logging.Formatter('%(name)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(log_level)
logging.basicConfig(
    filename='control.log',
    encoding='utf-8', 
    level=logging.DEBUG
)

class Program:
    active_function = None

    def __init__(self, function: ProgramFunctionBase) -> None:

        self.context = {'phase': 'rest'}
        self.return_history: List[str] = []
        self.event_history: List[Event] = []
        self.connection: ServerConnection = None
        self.event: Event = None
        self.active_function = function
        self.message = None
        self.deployment_ids = None
        self.name = self.active_function.__class__.__name__
        self.name = self.name.lower()
        self.call(function)
        log.debug('instantiating new Program "{}"'.format(self.name))
        self.logger = log


    def call(self, function: ProgramFunctionBase):
        log.info('ControlBot "{}" calling function: {}'.format(self.name, {function.__class__.__name__}))
        self.active_function = function
        self.active_function.context = self

    def run(self, connection: ServerConnection, event: Event):
        log.info('program "{}" is calling "{}" on a new message'.format(self.name, self.active_function.__class__.__name__))
        message = event.message()
        log.debug('processor received message: {}'.format(message))
        self.message = message
        self.event = event
        self.connection = connection
        self.event_history.append(event)
        log.debug('about to run {}'.format(self.active_function.__class__.__name__))
        ret = self.active_function.run()
        log.debug('{} returned: {}'.format(self.active_function.__class__.__name__, ret))
        self.return_history.append(ret)
        return ret


    def last_events(self, type, sender=None, n=1):
        '''
        retrieves the last 'n' events of type message 'type' with an optional filter for the sender nick/id
        of the last 'n' messages that are pulled 
        '''
        # look at the most recent set number messages
        lookback = 30
        log.debug('about to pull the last {} messages of type "{}" from sender={}'.format(lookback, type, sender))
        to_inspect = self.event_history if len(self.event_history) < lookback else self.event_history[:lookback]
        print('EVENT HISTORY:', list(map(lambda x: x.message() ,self.event_history)))
        last: List[Event] = list(filter(
            lambda x:
                (x.message().split('::')[::-1].pop() == type) and 
                ( (not sender) or (x.source == sender) ),
            to_inspect
        ))
        if len(last) < 1 and lookback > 1:
            log.warning('no lookback history available for the "{}" program'.format(self.name))
            return None
        log.debug('sucessfully pulled history for the "{}" program'.format(self.name))
        return last[-1]


    def target(self):
        return self.event.target




class ProgramFunctionBase(ABC):

    @property
    def name(self) -> str:
        return self._context.name
    
    @property
    def context(self) -> Program:
        return self._context

    @property
    def message(self) -> str:
        return self._context.message

    @property
    def event(self) -> Event:
        return self._context.event

    @property
    def logger(self) -> Event:
        return self._context.logger

    @property
    def deployment_ids(self) -> Event:
        return self._context.deployment_ids

    @property
    def event_history(self) -> str:
        return self._context.event_history

    @property
    def connection(self) -> ServerConnection:
        return self._context.connection

    @property
    def return_history(self) -> str:
        return self._context.return_history

    def last_events(self, type, sender=None, n=1):
            return self._context.last_events(type, sender, n)

    @context.setter
    def context(self, context: Program) -> None:
        self._context = context

    @abstractmethod
    def run(self) -> None:
        pass
