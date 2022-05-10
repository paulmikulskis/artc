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
from messages.types import PiError
from run.influx_wrapper import InfluxStatWriter
from os.path import join, dirname, abspath
from dotenv import load_dotenv
from client.miner_client.braiins_asic_client import BraiinsOsClient
from supabase import create_client, Client

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

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

url: str = SUPABASE_URL
key: str = SUPABASE_KEY
supabase: Client = create_client(url, key)

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
            return True

        # !!!!!! ?
        # self.do_command(e, e.arguments[0])

        print('\nreceived message from controller:\n    {}'.format(the_message))
        
        # this block will fire if the command is sent as a public message
        # to the channel of this node's deployment ID
        if e.target == '#'+self.nickname:
            # if the message is intended for this PiBot, then parse:
            result: Tuple[any or None, PiError or None] = parseMessage(the_message)
            error = result[1]
            if error is not None:
                # post error to subapase table for this deploymentid
                data = supabase.table('errors').insert(
                    {
                        'deployment_id': self.nickname,
                        'message': str(error),
                        'severity': 10,
                        'code': 500
                        }
                    )
                # data.execute()
                print('NODE ERROR:', error)

            else:
                handleMessageResponse = result[0]
                return True

        return True

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
            result: List[any or None, PiError or None] = parseMessage(cmd)
            error = result[1]
            if error is not None:
                # post error to subapase table for this deploymentid
                data = supabase.table('errors').insert(
                    {
                        'deployment_id': self.nickname,
                        'message': str(error),
                        'severity': 10,
                        'code': 500
                        }
                    ).execute()

            else:
                handleMessageResponse = result[0]
                return True

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
    errors = list(map(lambda y: y[1], filter(lambda x: x[1] is not None, stats.items())))
    for error in errors:
        log.error(error)
        # supabase.table('errors').insert(
        #     {
        #         'deployment_id': irc_connection.nickname,
        #         'message': str(error),
        #         'severity': 10,
        #         'code': error.httpCode
        #         }
        #     ).execute()
    stats = {k: (v[0] if v[0] else v[1]) for k, v in stats.items()}
    error = influx_stat_writer.write_dict('main_stats', stats)
    if error is not None:
        # supabase.table('errors').insert(
        #     {
        #         'deployment_id': irc_connection.nickname,
        #         'message': str(error),
        #         'severity': 10,
        #         'code': error.httpCode
        #         }
        #     ).execute()
        log.debug('stats successfully written to InfluxDB')
    try:
        print('MAIN STATS:', stats)
        stats = json.dumps(stats)
        log.debug('wrote stats: {}'.format(stats))
        irc_connection.privmsg('#'+irc_connection.nickname, 'stats::'+stats)
    except:
        log.error('unable to jsonify stats received by stat_map functiong, skipping IRC communications!')
    
    # log.debug('getting miner temperatures')
    # miner_temps = device_map['miners'].get_temps()
    # if miner_temps[1]:
        # supabase.table('errors').insert(
        #     {
        #         'deployment_id': irc_connection.nickname,
        #         'message': str(miner_temps[1]),
        #         'severity': 10,
        #         'code': 500
        #         }
        #     ).execute()
        # log.error('miner temp error:', error)
    # else:
        # miner_temps = miner_temps[0]
        # influx_stat_writer.write_dict('miner_temps', miner_temps)
        # log.debug('successfully wrote miner temperatures to InfluxDB')
    
    # is_mining: dict = braiins.is_mining()
    # for k, v in is_mining.items():
    #     if one of the values in the return dict is an error (not a bool)
    #     if not isinstance(v, bool):
            # supabase.table('errors').insert(
            #     {
            #         'deployment_id': irc_connection.nickname,
            #         'message': str(v),
            #         'severity': 10,
            #         'code': 500
            #         }
            #     ).execute()
            # pass
    # log.debug('polled if ASICs are mining:', is_mining)
    #is_mining = False
    # temps = braiins.get_temperature_list()
    # if temps[1]:
    #     temps: MinerAPIError = str(temps[1])
        # supabase.table('errors').insert(
        #     {
        #         'deployment_id': irc_connection.nickname,
        #         'message': str(temps),
        #         'severity': 10,
        #         'code': 501
        #         }
        #     ).execute()
    # else:
    #     temps: Dict[str, List[Tuple[str]]] = temps[0]
    #     for k, v in temps.items():
    #         try:
    #             temps[k] = {**{'board_'+str(d[2]): {'board': d[0], 'chip': d[1]} for d in v}, 'mining': is_mining.get(k) or 'UNKNOWN'}
    #         except Exception as e:
    #             print('UNHANDLED ERROR !! (check this out and add to PiErrors!!):', e)
    #temps={}            
    # irc_connection.privmsg('#'+irc_connection.nickname, 'miner::'+json.dumps(temps))


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

