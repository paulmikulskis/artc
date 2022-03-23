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

import more_itertools
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler()
scheduler.start() 

# Get the path to the directory this file is in
BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../.base.env'))


class ControlBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, nodenicks, port=6667, password='1234count', stat_interval=2):
        if isinstance(os.environ.get("STAT_WRITER_INTERVAL_SEC"), int): stat_interval = os.environ.get("STAT_WRITER_INTERVAL_SEC")
        SingleServerIRCBot.__init__(self, [(server, port, password)], nickname, nickname)
        self.channel = channel
        self.stat_interval = stat_interval
        self.password = password
        self.nickname = nickname
        self.nodenicks = nodenicks


    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)
        for nick in self.nodenicks:
            print('joining #'+nick)
            c.join('#'+nick)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        print('received public message:', e.arguments)
        if (e.target[1:] == self.nickname) or (e.target[1:] in self.nodenicks):
            if(e.arguments[0].split('::')[0] == 'stats'):
                self.process_stats(e.arguments[0].split('::')[1])

        return

    def process_stats(self, stats):
        print('\nheard stats from IRC server:')
        print(stats)

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


class ControlBotClient(SimpleIRCClient):

    def __init__(
        self,
        server_list,
        nickname,
        realname,
        _=None,
        recon=ExponentialBackoff(),
        **connect_params,
    ):
        super().__init__()
        self.__connect_params = connect_params
        self.channels = IRCDict()
        specs = map(ServerSpec.ensure, server_list)
        self.servers = more_itertools.peekable(itertools.cycle(specs))
        self.recon = recon

        self._nickname = nickname
        self._realname = realname
        for i in [
            "disconnect",
            "join",
            "kick",
            "mode",
            "namreply",
            "nick",
            "part",
            "quit",
        ]:
            self.connection.add_global_handler(i, getattr(self, "_on_" + i), -20)
          
        self._connect()

    def on_welcome(self, c, e):
        #c.join('#'+self.nickname)
        c.join('#main')

    def _connect(self):
        """
        Establish a connection to the server at the front of the server_list.
        """
        server = self.servers.peek()
        try:
            self.connect(
                server.host,
                server.port,
                self._nickname,
                server.password,
                ircname=self._realname,
                **self.__connect_params,
            )
        except irc.client.ServerConnectionError:
            print('CONNECTION ERROR!')
            pass

    def _on_disconnect(self, connection, event):
        self.channels = IRCDict()
        self.recon.run(self)

    def _on_join(self, connection, event):
        print('JOINED')
        ch = event.target
        nick = event.source.nick
        if nick == connection.get_nickname():
            self.channels[ch] = Channel()
        self.channels[ch].add_user(nick)

    def _on_kick(self, connection, event):
        nick = event.arguments[0]
        channel = event.target

        if nick == connection.get_nickname():
            del self.channels[channel]
        else:
            self.channels[channel].remove_user(nick)

    def _on_mode(self, connection, event):
        t = event.target
        if not irc.client.is_channel(t):
            # mode on self; disregard
            return
        ch = self.channels[t]

        modes = irc.modes.parse_channel_modes(" ".join(event.arguments))
        for sign, mode, argument in modes:
            f = {"+": ch.set_mode, "-": ch.clear_mode}[sign]
            f(mode, argument)

    def _on_namreply(self, connection, event):
        """
        event.arguments[0] == "@" for secret channels,
                          "*" for private channels,
                          "=" for others (public channels)
        event.arguments[1] == channel
        event.arguments[2] == nick list
        """

        ch_type, channel, nick_list = event.arguments

        if channel == '*':
            # User is not in any visible channel
            # http://tools.ietf.org/html/rfc2812#section-3.2.5
            return

        for nick in nick_list.split():
            nick_modes = []

            if nick[0] in self.connection.features.prefix:
                nick_modes.append(self.connection.features.prefix[nick[0]])
                nick = nick[1:]

            for mode in nick_modes:
                self.channels[channel].set_mode(mode, nick)

            self.channels[channel].add_user(nick)

    def _on_nick(self, connection, event):
        before = event.source.nick
        after = event.target
        for ch in self.channels.values():
            if ch.has_user(before):
                ch.change_nick(before, after)

    def _on_part(self, connection, event):
        nick = event.source.nick
        channel = event.target

        if nick == connection.get_nickname():
            del self.channels[channel]
        else:
            self.channels[channel].remove_user(nick)

    def _on_quit(self, connection, event):
        nick = event.source.nick
        for ch in self.channels.values():
            if ch.has_user(nick):
                ch.remove_user(nick)

    def die(self, msg="Bye, cruel world!"):
        """Let the bot die.

        Arguments:

            msg -- Quit message.
        """

        self.connection.disconnect(msg)
        sys.exit(0)

    def disconnect(self, msg="I'll be back!"):
        """Disconnect the bot.

        The bot will try to reconnect after a while.

        Arguments:

            msg -- Quit message.
        """
        self.connection.disconnect(msg)

    @staticmethod
    def get_version():
        """Returns the bot version.

        Used when answering a CTCP VERSION request.
        """
        return f"Python irc.bot ({irc._get_version()})"

    def jump_server(self, msg="Changing servers"):
        """Connect to a new server, possibly disconnecting from the current.

        The bot will skip to next server in the server_list each time
        jump_server is called.
        """
        if self.connection.is_connected():
            self.connection.disconnect(msg)

        next(self.servers)
        self._connect()

    def on_ctcp(self, connection, event):
        """Default handler for ctcp events.

        Replies to VERSION and PING requests and relays DCC requests
        to the on_dccchat method.
        """
        nick = event.source.nick
        if event.arguments[0] == "VERSION":
            connection.ctcp_reply(nick, "VERSION " + self.get_version())
        elif event.arguments[0] == "PING":
            if len(event.arguments) > 1:
                connection.ctcp_reply(nick, "PING " + event.arguments[1])
        elif (
            event.arguments[0] == "DCC"
            and event.arguments[1].split(" ", 1)[0] == "CHAT"
        ):
            self.on_dccchat(connection, event)

    def on_dccchat(self, connection, event):
        pass

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_privmsg(self, c, e):
        pass

    def on_pubmsg(self, c, e):
        pass

    def on_dccmsg(self, c, e):
        pass

    def on_dccchat(self, c, e):
        pass

    def process(self):
        self.reactor.process_once()





def statloop():
    pass


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

    nodenicks = ['pibot', 'jumba_bot']
    server = 'sungbean.com'
    nickname = 'pilisten'
    channel = '#main'
    port = 6667
    password = '1234count'
    nick = 'control_bot_server'

    bot = ControlBot(channel, nickname, server, nodenicks, port)
    bot.reactor.scheduler.execute_every(bot.stat_interval, functools.partial(statloop))
    bot.start()


if __name__ == '__main__':
    main()
