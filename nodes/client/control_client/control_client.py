#! /usr/bin/env python
#
# Example program using irc.bot.
#
# Joel Rosdahl <joel@rosdahl.net>

"""A simple example bot.

This is an example bot that uses the SingleServerIRCBot class from
irc.bot.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.

The known commands are:

    stats -- Prints some channel information.

    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.

    die -- Let the bot cease to exist.

    dcc -- Let the bot invite you to a DCC CHAT connection.
"""

from datetime import datetime, timedelta
import functools
import itertools
import json
import logging
import os
import sys
import threading
import time
import irc
from  irc.bot import SingleServerIRCBot, Channel, ExponentialBackoff, ServerSpec
from irc.client import SimpleIRCClient, ip_numstr_to_quad, ip_quad_to_numstr
from irc.dict import IRCDict
from os.path import join, dirname, abspath
from dotenv import load_dotenv
from threading import Thread

from client.control_client.stats import MessageProcessor, Program
from client.control_client.programs.HandOnOffTest import HandOnOffTest
from client.control_client.programs.JacuzziTest import JacuzziTest


# Get the path to the directory this file is in
BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../../../.base.env'))
log_level = os.environ.get("LOG_LEVEL")
log_type = os.environ.get("LOG_TYPE")
if log_type not in ['FULL', 'CLEAN']:
    log_type = 'FULL'

if log_level not in list(map(lambda x: x[1], logging._levelToName.items())):
    log_level = 'INFO'

ch = logging.StreamHandler()
log = logging.getLogger(__name__.split('.')[-1])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') if log_type == 'FULL' else logging.Formatter('%(name)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(log_level)


class ControlBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, nodenicks, port=6667, password='1234count', stat_interval=2):
        if isinstance(os.environ.get("STAT_WRITER_INTERVAL_SEC"), int): stat_interval = os.environ.get("STAT_WRITER_INTERVAL_SEC")
        SingleServerIRCBot.__init__(self, [(server, port, password)], nickname, nickname)
        self.channel = channel
        self.stat_interval = stat_interval
        self.password = password
        self.nickname = nickname
        self.nodenicks = nodenicks
        log.info('ControlBot connecting to {}:{} on {}'.format(server, port, nodenicks.append('main')))
        log.debug('creating new message processor with nodenicks={}'.format(nodenicks))

        programs = [
            Program(JacuzziTest(target_temp=98)),
        ]
        self.processor = MessageProcessor(self.nodenicks, programs)


    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)
        for nick in self.nodenicks:
            log.info('joining channel #'+nick)
            c.join('#'+nick)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, connection, event):
        log.debug('received public message: {}'.format(event.arguments))
        if (event.target[1:] == self.nickname) or (event.target[1:] in self.nodenicks):
            self.processor.process(connection, event)
        return

    def on_dccmsg(self, c, e):
        return
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        return
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def do_command(self, e, cmd):
        if '::' in cmd:
            print('private command message received for {}'.format(self.nickname))
        return
       


def statloop():
    pass


def main():
    import sys

    if len(sys.argv) != 4:
        print("Usage: testbot <server[:port]> <channel> <nickname> <password>")
        server = os.environ.get("IRC_HOST")
        nickname = os.environ.get("CONTROLLER_NICKNAME")
        channel = '#main'
        port = os.environ.get("IRC_PORT")

        if None in [server, nickname, channel, port]:
            print('!! Error: these variables were not found in base.env either, exiting...')
            sys.exit(1)


    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    nodenicks = os.environ.get("NODENICKS")
    print('NODENICKS')
    if nodenicks is None:
        log.warn('NODENICKS not found in base.env, using defaults of [default, jumba_bot]')
        nodenicks = ['default', 'jumba_bot']
    else:
        nodenicks = nodenicks.split(',')
    server = os.environ.get("IRC_HOST")
    nickname = os.environ.get("CONTROLLER_NICKNAME")
    # channel only serves as a default channel that the control bot joins
    channel = '#main'
    port = os.environ.get("IRC_PORT")
    try:
        port = int(port)
    except:
        log.error('PORT found in base.env, but cannot be converted to a needed integer')
        sys.exit(1)
    password = os.environ.get("COMMUNICATIONS_MASTER_PASSWORD")
    bot = ControlBot(channel, nickname, server, nodenicks, port)
    bot.reactor.scheduler.execute_every(bot.stat_interval, functools.partial(statloop))
    bot.start()


if __name__ == '__main__':
    main()
