from __future__ import unicode_literals

__author__ = 'Kibur'

import requests
from datetime import datetime, timedelta
import json
from threading import Thread
import irc.bot
import argparse
from colorama import init, Fore
import random
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, client_id, token, channel):
        self.client_id = client_id
        self.token = token
        self.channel = channel
        self.api = 'https://api.twitch.tv/helix/'
        self.headers = {'Client-ID': client_id}
        self.old = {
            'api': 'https://api.twitch.tv/kraken/',
            'headers': {
                'Client-ID': client_id,
                'Accept': 'application/vnd.twitchtv.v5+json'
            }
        }
        self.is_online = False
        colour_codes = vars(Fore)
        self.colours = {
            'previous': None,
            'all': [
                colour_codes.get(c) for c in colour_codes
                if c not in ('BLACK', 'WHITE', 'LIGHTBLACK_EX', 'RESET')
            ]
        }
        del colour_codes

        print('Connecting to Twitch server')
        server, port = 'irc.chat.twitch.tv', 6667
        super(TwitchBot, self).__init__(
            [(server, port, token)], username, username
        )

    def on_welcome(self, c, e):
        print('Joining #{}'.format(self.channel))

        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join('#{}'.format(self.channel))

        r = requests.get(
            '{}streams?user_login={}'.format(self.api, self.channel),
            headers=self.headers
        ).json()

        if any(r.get('data')):
            self.is_online = True

        r = requests.get(
            '{}users?login={}'.format(self.old.get('api'), self.channel),
            headers=self.old.get('headers')
        ).json()
        channel_id = r.get('users')[0].get('_id')
        r = requests.get(
            '{}channels/{}'.format(self.old.get('api'), channel_id),
            headers=self.old.get('headers')
        ).json()

        print(
            '({}) {} [{}]'.format(
                r.get('game'),
                r.get('status'),
                'ONLINE' if self.is_online else 'OFFLINE'
            ),
            end='\n\n'
        )

    def on_pubmsg(self, c, e):
        display_name, timestamp = False, False

        if e.arguments[0][:1] not in ('!', '?', '.'):
            for tag in e.tags:
                if tag.get('key') == 'display-name':
                    display_name = tag.get('value')
                if tag.get('key') == 'tmi-sent-ts':
                    timestamp = int(tag.get('value')) / 1000

                if display_name and timestamp:
                    break

            if display_name in ('Nightbot'):
                return

            msg_time = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            msg = ''.join(
                i if ord(i) < 10000 else '\ufffd' for i in e.arguments[0]
            )
            colour = random.choice(self.colours.get('all'))

            while colour == self.colours.get('previous'):
                colour = random.choice(self.colours.get('all'))

            self.colours['previous'] = colour

            chat = '[{}]{}{}{}: {}'.format(
                msg_time, colour, display_name, Fore.RESET, msg
            )
            print(chat)


class TwitchIRC:
    def __init__(self, username, client_id, token, channel):
        self.running = True
        self.username = username
        self.client_id = client_id
        self.token = 'oauth:{}'.format(token)
        self.channel = channel
        self.bot = TwitchBot(
            self.username, self.client_id, self.token, self.channel
        )
        self.bot._connect()
        self.session = PromptSession('ME: ')

        th1 = Thread(target=self.irc_bot, args=(self,))
        th1.start()
        th2 = Thread(target=self.interactive_shell, args=(self,))
        th2.start()

    def irc_bot(self, data):
        while self.running:
            self.bot.reactor.process_once(0.2)

    def interactive_shell(self, data):
        while self.running:
            with patch_stdout():
                command = self.session.prompt()

            if command == 'quit()':
                self.running = False
                self.bot.reactor.disconnect_all()
            else:
                self.bot.connection.privmsg(
                    '#{}'.format(self.channel), command
                )

def main():
    parser = argparse.ArgumentParser(description='Twitch IRC Bot by Kibur')
    parser.add_argument('-l', '--login', required=True, help='Twitch Username')
    parser.add_argument('-c', '--channel', help='Twitch Channel')

    args = parser.parse_args()
    profile = args.login
    channel = args.channel or profile
    creds = False

    # Colorama init
    init(autoreset=True)

    with open('./twitch_cred.json', mode='r', encoding='UTF-8') as f:
        data = (d for d in json.load(f) if d.get('profile') == profile)
        creds = next(data)

    if not creds:
        print('No credentials for {} found!'.format(profile))
        return

    iarc = TwitchIRC(
        creds.get('profile'),
        creds.get('client_id'),
        creds.get('token'),
        channel
    )


if __name__ == '__main__':
    main()
