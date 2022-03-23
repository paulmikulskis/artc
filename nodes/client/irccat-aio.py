#! /usr/bin/env python
#
# Example program using irc.client.
#
# This program is free without restrictions; do anything you like with
# it.

from sqlite3 import connect
import string
import sys
import argparse
import itertools
import asyncio
from typing import List

import irc.client_aio
import irc.client
import jaraco.logging
from irc.client_aio import AioSimpleIRCClient
from irc.client import SimpleIRCClient
from irc.client_aio import AioReactor

from quart import Quart, request
import quart.flask_patch

app = Quart(__name__)

target = None
        
class AsyncIRCClient(SimpleIRCClient):

    reactor_class = AioReactor

    def __init__(
        self, 
        host: str, 
        port: int, 
        nick: str, 
        nodenicks: List[str],
        password=None
        ):
            super().__init__()
            self.host = host
            self.port = port
            self.nick = nick
            self.nodenicks = nodenicks
            self.password = password
            self.loop = self.reactor.loop


    def connect(self):
        try:
            self.connection = self.loop.run_until_complete(
                self.reactor.server().connect(
                    self.host, self.port, self.nick, self.password
                )
            )
        except irc.client.ServerConnectionError:
            print(sys.exc_info()[1])
            raise SystemExit(1)

        except irc.client.ServerConnectionError:
            print(sys.exc_info()[1])
            raise SystemExit(1)


    def get_loop(self):
        return self.reactor.loop

    def on_welcome(self, connection, event):
        for id in self.nodenicks + ['main']:
            print('connecting to {}'.format('#'+id))
            connection.join('#'+id)


    def on_join(self, connection, event):
        connection.read_loop = asyncio.ensure_future(
            complete_asyncronously(connection), loop=connection.reactor.loop
        )

    def on_disconnect(self, connection, event):
        raise SystemExit()


    def message(self, target, messag):
        self.connection.privmsg(target, messag)

    def start(self):
        self.reactor.process_forever()



async def complete_asyncronously(connection):
    pass



def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('server')
    parser.add_argument('nickname')
    parser.add_argument('target', help="a nickname or channel")
    parser.add_argument('--password', default=None, help="optional password")
    parser.add_argument('-p', '--port', default=6667, type=int)
    jaraco.logging.add_arguments(parser)
    return parser.parse_args()


def main():
    global target
    
    client = AsyncIRCClient(
        'sungbean.com',
        6667,
        'control_bot',
        ['jumba_bot', 'pibot']
        )
    client.connect()

    @app.route("/")
    async def home():
        return "Hello, World!"

    @app.route("/command", methods=['POST'])
    async def command():
        data = await request.get_json(force=True)
        print('REQEST DATA:', data)
        id = data['id']
        command = data['command']
        param_string = data['params']
        params = param_string
        if params is not None:
            params = params.split(',')

        print('sending to {}, {}'.format('#'+id, 'cmd::'+command+'::'+param_string))
        client.message('#'+id, 'cmd::'+command+'::'+param_string)
        client.message('#main', 'cmd::'+command+'::'+param_string)
        return 'success'


    # start the server app and the IRC bot:
    try:
        loop = client.get_loop()
        print('FIRST!')
        loop.create_task(app.run_task())
        print('=== about to start client...')
        client.start()
        print('SECOND!')
    finally:
        loop.close()

    print('done?')


if __name__ == '__main__':
    main()
