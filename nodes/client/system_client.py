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
import os
import time
from  irc.bot import SingleServerIRCBot
from irc import strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr, ServerConnection
from messages.scribe import parseMessage
from system.system import device_map
from run.influx_wrapper import InfluxStatWriter
from os.path import join, dirname, abspath
from dotenv import load_dotenv

from system.system import stat_map

# Get the path to the directory this file is in
BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../.base.env'))


class PiBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, password='1234count', stat_interval=2):
        if isinstance(os.environ.get("STAT_WRITER_INTERVAL_SEC"), int): stat_interval = os.environ.get("STAT_WRITER_INTERVAL_SEC")
        SingleServerIRCBot.__init__(self, [(server, port, password)], nickname, nickname)
        self.channel = channel
        self.stat_interval = stat_interval
        self.password = password
        self.nickname = nickname

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)
        c.join('#'+self.nickname)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        print('a args:', a)
        print('e args', e.arguments)
        if len(a) > 1 and strings.lower(a[0]) == strings.lower(
            self.connection.get_nickname()
        ):
            self.do_command(e, a[1].strip())
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
def statloop(influx_stat_writer: InfluxStatWriter, irc_connection: ServerConnection):
    print('\nsending stats...')
    stats = {k: v() for k, v in stat_map.items()}
    influx_stat_writer.write_dict('test', stats)
    irc_connection.privmsg('#'+irc_connection.nickname, ''+str(stats))


def main():
    import sys

    if len(sys.argv) != 4:
        print("Usage: testbot <server[:port]> <channel> <nickname> <password>")
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
    influx_stat_writer = InfluxStatWriter(os.environ.get("INFLUX_HOST"))
    device_map['flow1'].listen()

    bot = PiBot(channel, nickname, server, port)
    bot.reactor.scheduler.execute_every(bot.stat_interval, functools.partial(statloop, influx_stat_writer, bot.connection))
    bot.start()

