
from operator import le
import string

from run.run import executeChangeCommand
from . import types

# putting this here in case we change the protocol later
FIELD_SEPRATATOR = '::'


def parseMessage(msg: string) -> bool or types.PiError :
    parts = msg.split(FIELD_SEPRATATOR)
    message_type = parts[0]
    print('message_type = "{}"'.format(message_type))
    print('is it a command? ... :{}'.format(message_type == types.Messages.COMMAND.value))
    if message_type == types.Messages.COMMAND.value:
        if len(parts) < 2: 
          return types.PiError(
            types.ErrorType.INVALID_PARAMS,
            'cmd msg received but no command specified',
            400
          )
        command_type = parts[1]
        if command_type == types.Commands.CHANGE_STATE.value:
          if len(parts) < 2: 
              return types.PiError(
                types.ErrorType.INVALID_PARAMS,
                'cmd CHANGE_STATE received but no arguments specified',
                400
              )
          else:
              args = parts[2].split(',')
              if len(args < 2):
                  return types.PiError(
                    types.ErrorType.INVALID_PARAMS,
                    'cmd CHANGE_STATE received but only {} arguments specified'.format(len(args)),
                    400
                  )
              return executeChangeCommand(*args)

          return False
    if message_type == types.Messages.STATPULL.value:
        return True

    return False