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

import functools
import json
import logging
import os
import time
from typing import Dict, List, Tuple
from  irc.bot import SingleServerIRCBot
from irc import strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr, ServerConnection
from messages.scribe import parseMessage
from client.miner_client.braiins_asic_client import MinerAPIError
from system.system import device_map
from run.influx_wrapper import InfluxStatWriter
from os.path import join, dirname, abspath
from dotenv import load_dotenv
from client.miner_client.braiins_asic_client import BraiinsOsClient


from system.system import stat_map, device_map

# Get the path to the directory this file is in
BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../.base.env'))

log_level = os.environ.get("LOG_LEVEL")
log_type = os.environ.get("LOG_TYPE")

if log_level not in list(map(lambda x: x[1], logging._levelToName.items())):
    log_level = 'INFO'
if log_type not in ['FULL', 'CLEAN']:
    log_type = 'FULL'

ch = logging.StreamHandler()
log = logging.getLogger('node_client')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') if log_type == 'FULL' else logging.Formatter('%(name)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(log_level)


class PiBot(SingleServerIRCBot):
    def __init__(self, channel, deployment_id, server, port=6667, password='1234count', stat_interval=6):
        if isinstance(os.environ.get("STAT_WRITER_INTERVAL_SEC"), int): stat_interval = os.environ.get("STAT_WRITER_INTERVAL_SEC")
        SingleServerIRCBot.__init__(self, [(server, port, password)], deployment_id, deployment_id)
        self.channel = channel
        self.stat_interval = stat_interval
        self.password = password
        self.nickname = deployment_id
        self.deployment_id = deployment_id

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)
        c.join('#'+self.nickname)
        print('joined the "{}" channel'.format('#'+self.nickname))

    def on_privmsg(self, c, e):
        log.debug('received a private message from {}: {}'.format(e.source.nick, e.arguments[0]))
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        the_message = e.arguments[0]
        log.debug('received a public message from {}: {}'.format(e.source.nick, the_message))
        #command = the_message.split(':')[0]

        # we don't want to do anything right now with the main channel, which is
        # only used more-or-less as a global firehose log of the system
        if e.target == '#main':
            log.info('received a message in the #main channel: {}'.format(e.arguments[0]))
            return 
        self.do_command(e, e.arguments[0])

        print('\nreceived message from controller:\n    {}'.format(the_message))
        
        # this block will fire if the command is sent as a public message
        # to the channel of this node's deployment ID
        if e.target == '#'+self.nickname:
            # if the message is intended for this PiBot, then parse:
            result = parseMessage(the_message)
            if result is not True:
                print(result)

        return

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
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
        nick = e.source.nick
        c = self.connection
        if '::' in cmd:
            print('received Pi command: {}'.format(cmd))
            result = parseMessage(cmd)
            if result is not True:
                print(result)

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = sorted(chobj.users())
                c.notice(nick, "Users: " + ", ".join(users))
                opers = sorted(chobj.opers())
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = sorted(chobj.voiced())
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        elif cmd == "dcc":
            dcc = self.dcc_listen()
            c.ctcp(
                "DCC",
                nick,
                "CHAT chat %s %d"
                % (ip_quad_to_numstr(dcc.localaddress), dcc.localport),
            )
        else:
            c.notice(nick, "Not understood: " + cmd)


'''
Main loop that defines the frequency of global stat updates
to the server and InfluxDB
'''
def statloop(influx_stat_writer: InfluxStatWriter, braiins: BraiinsOsClient, irc_connection: ServerConnection):
    log.info('collecting and sending stats...')
    stats = {k: v() for k, v in stat_map.items()}
    influx_stat_writer.write_dict('main_stats', stats)
    log.debug('stats successfully written to InfluxDB')
    try:
        stats = json.dumps(stats)
        log.debug('wrote stats:', stats)
        irc_connection.privmsg('#'+irc_connection.nickname, 'stats::'+stats)
    except:
        log.error('unable to jsonify stats received by stat_map functiong, skipping IRC communications!')
    
    log.debug('getting miner temperatures')
    miner_temps = device_map['miners'].get_temps()
    influx_stat_writer.write_dict('miner_temps', miner_temps)
    log.debug('successfully wrote miner temperatures to InfluxDB')
    
    is_mining = braiins.is_mining()
    log.debug('polled if ASICs are mining:', is_mining)
    #is_mining = False
    temps = braiins.get_temperature_list()
    if temps[1]:
        temps: MinerAPIError = str(temps[1])
    else:
        temps: Dict[str, List[Tuple[str]]] = temps[0]
        for k, v in temps.items():
                temps[k] = {**{'board_'+str(d[2]): {'board': d[0], 'chip': d[1]} for d in v}, 'mining': is_mining.get(k) or 'UNKNOWN'}
    #temps={}            
    irc_connection.privmsg('#'+irc_connection.nickname, 'miner::'+json.dumps(temps))


def main():
    import sys

    if len(sys.argv) != 4:
        log.error("Usage: testbot <server[:port]> <channel> <nickname> <password>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            log.error("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    # instantiate loop-running classes, writers, listeners here:
    log.info('instantiating influx client at {}'.format(os.environ.get("INFLUX_HOST")))
    influx_stat_writer = InfluxStatWriter(os.environ.get("INFLUX_HOST"))
    log.info('connecting BraiinsOs client at {}:{}'.format(os.environ.get("MINING_HOST"), os.environ.get("MINING_PASSWORD")))
    braiins = BraiinsOsClient(os.environ.get("MINING_HOST"), password=os.environ.get("MINING_PASSWORD"))
    log.info('creating IRC bot, channel="{}", nickname="{}", server="{}", port="{}"'.format(channel, nickname, server, port))
    bot = PiBot(channel, nickname, server, port)

    # device_map['flow1'].listen()
    bot.reactor.scheduler.execute_every(bot.stat_interval, functools.partial(statloop, influx_stat_writer, braiins, bot.connection))
    log.info('🚀 calling bot.start()... ')
    bot.start()

