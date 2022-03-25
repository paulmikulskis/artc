from enum import Enum
import string

'''
Defines the types of messages that the server and nodes
will be sending between one another
'''
class Messages(Enum):
    NODE_COM = 'node'
    COMMAND = 'cmd'
    ERROR = 'err'
    STATPUSH = 'stpsh'
    STATPULL = 'stpul'


'''
Defines the types of commands the server can send to the nodes
'''
class Commands(Enum):
    # for reading a value
    READ = 'read'
    # for altering the value of a pin
    # e.x. chng::pump1,on
    CHANGE_STATE = 'chng'
    # for running a a server function
    # e.x. func::miners::start
    FUNCTION = 'func'



'''
Defines the types of messages the nodes will send to the API server
'''
class NodeCommunications(Enum):
    METADATA = 'meta'


class ErrorType(Enum):
    METHOD_NOT_FOUND = 32601
    INVALID_JSON_REQUEST = 32600
    INVALID_PARAMS = 32602
    INTERNAL_ERROR = 32603
    PROCEDURE_IS_METHOD = 32604
    PARSE_ERROR = 32700
    NO_DEVICE = 42069


ErrorDict = {
    32601: 'METHOD_NOT_FOUND',
    32600: 'INVALID_JSON_REQUEST',
    32602: 'INVALID_PARAMS',
    32603: 'INTERNAL_ERROR',
    32604: 'PROCEDURE_IS_METHOD',
    32700: 'PARSE_ERROR',
    42069: 'NO DEVICE'
}


class PiError:

    def __init__(self, etype: ErrorType, message: string, httpCode: int = 200) -> any:
        self.type = etype
        self.message = message
        self.httpCode = httpCode

    def __str__(self):
        return '{}: {} HTTP {}\n{}'.format(
            self.type.value, 
            ErrorDict.get(self.type.value), 
            self.httpCode, 
            self.message
            )

    def print(self):
        return '{}::{}::{}::{}'.format(
            self.type.value, 
            ErrorDict.get(self.type.value), 
            self.httpCode, 
            self.message
            )
