from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty
import logging
from re import L
from irc.client import ServerConnection, Event
import sys
from typing import List

ch = logging.StreamHandler()
log = logging.getLogger(__name__.split('.')[-1])

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
ch.setFormatter(formatter)
log.addHandler(ch)
logging.basicConfig(
    filename='control.log',
    encoding='utf-8', 
    level=logging.DEBUG
)

class Program:
    active_function = None

    def __init__(self, function: ProgramFunctionBase) -> None:

        self.call(function)
        self.context = {}
        self.return_history: List[str] = []
        self.event_history: List[Event] = []
        self.connection: ServerConnection = None
        self.event: Event = None
        self.active_function = function
        self.message = None
        self.deployment_ids = None
        self.name = self.active_function().__class__.__name__


    def call(self, function: ProgramFunctionBase):
        print('should see a log by here...')
        log.info("Program: calling next function".format({function().__class__.__name__}))
        self.active_function = function
        self.active_function.context = self

    def run(self, connection: ServerConnection, event: Event):
        message = event.message()
        self.message = message
        self.event = event
        self.connection = connection
        self.event_history.append(event)
        ret = self.active_function.run(self)
        self.return_history.append(ret)
        return ret


    def last_events(self, type, sender=None, n=1):
        '''
        retrieves the last 'n' events of type message 'type' with an optional filter for the sender nick/id
        of the last 'n' messages that are pulled 
        '''
        # look at the most recent 30 messages
        to_inspect = self.event_history if len(self.event_history) < 30 else self.event_history[:30]
        last: List[Event] = list(filter(
            lambda x: 
                (x.message().split('::')[::-1].pop() == type) and 
                ( (not sender) or (x.source == sender) ),
            to_inspect
        ))
        if len(last) < 1:
            return None
        return last[0]


    def target(self):
        return self.event.target




class ProgramFunctionBase(ABC):

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

    @context.setter
    def context(self, context: Program) -> None:
        self._context = context

    @abstractmethod
    def run(self) -> None:
        pass



class TestFunction(ProgramFunctionBase):

    def run(self) -> bool:
        message = self.message
        message_history = self.message_history
        return_history = self.return_history
        connection = self.connection

        if len(return_history) > 3:
            print('had more than 3 entries!', message_history)
            print('clearing memory...')
            return_history = []

        return message
        


