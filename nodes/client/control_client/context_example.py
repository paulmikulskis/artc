'''
This file is totally unrelated to the functionality of this software.
It is here merely to serve as a sake of example on how to use the Abstract Base Class
and context design pattern outlined here: 
  https://refactoring.guru/design-patterns/state/python/example#example-0--main-py

The script does the following:
  - defines a "Function" called TestFunction 
      - the TestFunction will take some message, and every 4th entry
        it will output all the messages sent
  - creates a "Program" with TestFunction
  - takes input from STDIN and runs TestFunction against each line

  Notice that TestFunction has access to certain self attributes without
  having them defined since they are declared in the Abstract Base Class.

  Also notice that the return value of TestFunction is saved automatically 
  and is accessible in future runs via the self.return_history attributes
'''
from __future__ import annotations
from abc import ABC, abstractmethod
import sys
from typing import List


class Program:
    active_function = None

    def __init__(self, function: ProgramFunctionBase) -> None:
        self.call(function)
        self.return_history: List[any] = []
        self.message_history: List[str] = []

    def call(self, function: ProgramFunctionBase):
        print(f"Context: Transition to {type(function).__name__}")
        self.active_function = function
        self.active_function.context = self

    def run(self, line):
        self.message: str = line
        self.message_history.insert(0, line)
        if len(self.message_history) > 600:
            self.message_history.pop()
        ret = self.active_function.run()
        self.return_history.append(ret)
        return ret


class ProgramFunctionBase(ABC):

    @property
    def context(self) -> Program:
        return self._context

    @property
    def message(self) -> str:
        return self._context.message

    @property
    def message_history(self) -> str:
        return self._context.message_history

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

    def run(self) -> None:
        message = self.message
        message_history = self.message_history
        return_history = self.return_history

        if len(return_history) > 3:
            print('had more than 3 entries!', message_history)
            print('clearing memory...')
            return_history = []

        return message
        

if __name__ == "__main__":

    program = Program(TestFunction())

    for line in sys.stdin:
        program.run(line)

