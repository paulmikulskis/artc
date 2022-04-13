#! /usr/bin/env python
#
# Example program using irc.client.
#
# This program is free without restrictions; do anything you like with
# it.

import os
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

from os.path import join, dirname, abspath
from dotenv import load_dotenv

from quart import Quart, request
from quart_cors import cors
import quart.flask_patch

app = Quart(__name__)
app = cors(app, allow_origin="*")

# Get the path to the directory this file is in
# and pull the .env file
BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../../.env'))
if not isinstance(os.environ.get("IRC_PROXY_HOST"), str):
    print('ERROR: unable to find IRC_PROXY_HOST in .env configuration... \
        \ncurrent environment variables:\n{}'.format(
            '\n'.join(os.environ.keys())
        ))
    sys.exit(69)
        
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
        for id in self.nodenicks:
            print('connecting to {}'.format('#'+id))
            connection.join('#'+id)

        connection.join('#main')


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
    parser.add_argument(
        'server',
        default='sungbean.com',
        help='hostname of the IRC server this client should proxy requests to',
        type=str
    )
    parser.add_argument(
        'nodenicks', 
        default='jumba_bot,pibot',
        help="comma-delineated list of nodes to proxy to \
            (#main is included by default)\n  e.g. jumba_bot,pibot",
        type=str
    )
    parser.add_argument(
        'nick',
        default='proxy_default',
        help='deployment ID of this IRC HTTP Proxy, default is proxy_default',
        type=str
    )
    parser.add_argument(
        '--password', 
        default=None, 
        help="optional password for the IRC server"
    )
    parser.add_argument(
        '-p', 
        '--port', 
        default=6667, 
        type=int
    )
    jaraco.logging.add_arguments(parser)
    return parser.parse_args()


def main():
    args = get_args()
    jaraco.logging.setup(args)
    
    nodenicks = args.nodenicks.split(',')
    nodenicks = [nick.strip() for nick in nodenicks]

    client = AsyncIRCClient(
        host=args.server,
        port=args.port,
        nick=args.nick,
        nodenicks=nodenicks,
        password=args.password
    )
    client.connect()

    @app.route("/")
    async def home():
        return "Hello, World!"


    @app.route("/command", methods=['POST'])
    async def command():
        # force=True will parse even without Application/Json Header
        data = await request.get_json(force=True)
        print('RECEIVED REQEST DATA:', data)
        id = data['id']
        command = data['command']
        param_string = data['params']
        params = param_string

        # params are delineated by a comma, in case wish to do something with them:
        if params is not None:
            params = params.split(',')

        print('sending to {}, {}'.format('#'+id, 'cmd::'+command+'::'+param_string))
        client.message('#'+id, 'cmd::'+command+'::'+param_string)
        # also send the message to #main for visibility via the system firehose
        client.message('#main', 'cmd::'+command+'::'+param_string)
        return 'success'


    @app.route("/control", methods=['POST'])
    async def control():
        # force=True will parse even without Application/Json Header
        data = await request.get_json(force=True)
        print('RECEIVED REQEST DATA:', data)
        id = data['id']
        command = data['command']
        param_string = data['params']
        params = param_string

        # params are delineated by a comma, in case wish to do something with them:
        if params is not None:
            params = params.split(',')

        print('sending to {}, {}'.format('#'+id, 'cmd::'+command+'::'+param_string))
        client.message('#'+id, 'control::'+command+'::'+param_string)
        # also send the message to #main for visibility via the system firehose
        # client.message('#main', 'cmd::'+command+'::'+param_string)
        return 'success'


    # start the server app and the IRC bot:
    try:
        loop = client.get_loop()
        loop.create_task(app.run_task(host='0.0.0.0'))
        print('=== about to start HTTP IRC client...')
        client.start()
        print('SECOND!')
    finally:
        loop.close()

    print('done?')


if __name__ == '__main__':
    main()
