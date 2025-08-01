import os
import re
import asyncio
import threading
import json

import psutil
import win32gui
import win32con

import keyboard

import requests
from pypresence import Presence

import time
from datetime import datetime

# funcs
async def joinGameSequence():
    await asyncio.sleep(2.5)
    hwnd = win32gui.FindWindow(None, 'Roblox')

    keyboard.send('shift')
    win32gui.SetForegroundWindow(hwnd)

    await asyncio.sleep(12)

    for key in ['\\', 'enter']:
        keyboard.send(key)
        await asyncio.sleep(0.1)

    await asyncio.sleep(5.5)

    for key in ['\\', 'enter', '\\']:
        keyboard.send(key)
        await asyncio.sleep(0.1)

    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_BOTTOM,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )

# class
class LogSniper:
    def __init__(self, data):
        self.data = data

        self.path = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox', 'logs')
        self.events = {}
        self.sendLogs = True

        self.webhooks = [hook for hook in self.data['Webhooks'].values()]
        self.pslink = data['Server']

        self.current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.currentLog = f'logs/{self.current_time}-logger-log'

        self.macro_start_time = time.time()

        self.biomedata = requests.get(data['PresetData']).json()

        # self.rpc = Presence(1371122806393143367)
        # self.rpc.connect()

        if 'logs' not in os.listdir():
            os.mkdir('logs')

        with open(self.currentLog, 'w') as file:
            file.write('')

        self.last_biome = None
        self.last_aura = 'None'
        self.synced = False

        self.last_position = 0
        self.prev_file = None
        self.blacklisted_files = []

    def event(self, coro):
        self.events[coro.__name__] = coro
        return coro

    # method
    def get_latest_log_file(self):
        files = [os.path.join(self.path, f) for f in os.listdir(self.path) if f.endswith('.log')]
        latest_file = max(files, key=os.path.getmtime)
        return latest_file

    def read_logfile(self, filepath):
        lines = None

        if not os.path.exists(filepath):
            print('DEBUG: File not found')
            return []

        if filepath in self.blacklisted_files:
            return

        if self.prev_file != filepath:
            self.last_position = 0

        self.prev_file = self.get_latest_log_file()

        with open(filepath, 'r', errors='ignore') as file:
            file.seek(self.last_position)
            lines = file.readlines()
            self.last_position = file.tell()

        return lines

    def convert_roblox_link(self, url): # credits to dan and yeswe
        game_pattern = r"https:\/\/www\.roblox\.com\/games\/(\d+)\/[^?]+\?privateServerLinkCode=(\d+)"
        share_pattern = r"https:\/\/www\.roblox\.com\/share\?code=([a-f0-9]+)&type=([A-Za-z]+)"
        match_game = re.match(game_pattern, url)

        if match_game:
            place_id = match_game.group(1)
            link_code = match_game.group(2)
            if place_id != "15532962292":
                return None
            link_code = ''.join(filter(str.isdigit, link_code))
            return f"roblox://placeID={place_id}&linkCode={link_code}"

        match_share = re.match(share_pattern, url)
        if match_share:
            code = match_share.group(1)
            share_type = match_share.group(2)
            if "Server" in share_type:
                share_type = "Server"
            elif "ExperienceInvite" in share_type:
                share_type = "ExperienceInvite"
            return f"roblox://navigation/share_links?code={code}&type={share_type}"

        return None

    def appendlogs(self, message):
        with open(self.currentLog, 'a') as file:
            file.write(f'{message}\n\n')

    def fetch_biome_data(self, biomedata):
        self.biomedata = biomedata

    def on_shutdown(self):
        timestamp = int(time.time())
        discord_time = f"<t:{timestamp}:R>"

        payload = {
            'username': self.data['webhook_name'],
            'avatar_url': self.data['webhook_avatar'],
            'embeds': [{
                'title': f'Macro Ended',
                'description': 'Macro has been stopped',
                'footer': {'text': self.data['Version']},
                'color': 0xFF0000
            }]
        }

        for hook in self.data['Webhooks'].values():
            response = requests.post(hook, json=payload)

            if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                print('Error encountered while requests.post, attempting to use default values to send...')
                payload.pop('avatar_url')

                response = requests.post(hook, json=payload)

            

            if 200 <= response.status_code < 300:
                pass
            elif str(response.status_code)[0] == '4':
                print('Still failed, pls open an issue')
            else:
                print('Unexpected response — possibly invalid avatar URL or other issue')

        print('Logger is shutting down...')

        return

    async def check_biome(self): # this function calls read logs and get latest already
        logpath = self.get_latest_log_file()
        log_lines = self.read_logfile(logpath)

        if not log_lines:
            return

        for line in reversed(log_lines):
            if '[FLog::Output]' in line:
                biome = None
                aura = None

                auramatch = re.search(r'"state":"Equipped \\"(.*?)\\"', line)

                aura = auramatch.group(1).replace('_', ' ').replace('â˜…', '⭐') if auramatch else self.last_aura
                self.last_aura = aura if auramatch else self.last_aura

                for biome in self.biomedata.keys():
                    if biome in line:
                        await self.biomedetected(biome, aura)

                        return

    # async methods
    async def biomedetected(self, biome, aura):
        firstTime = self.last_biome is None
        updateCounter = False
        payload = {
            'username': self.data['webhook_name'] + ' | Biomes',
            'content': '@everyone' if biome in (self.biomedata['glitch_keywords'] + self.biomedata['dream_keywords']) else '',
            'avatar_url': self.data['webhook_avatar']
        }

        embeds = []
        embed1 = {}
        embed2 = {}

        timestamp = int(time.time())
        discord_time = f"<t:{timestamp}:F>"

        # --- Rich Presence (DISABLED) ---
        # self.rpc.update(
        #     large_image=biome.lower().replace(' ', ''),
        #     large_text=biome,
        #     state='Sols RNG',
        #     details=f'Equipping {aura}',
        #     start=self.macro_start_time
        # )


        # webhook operations
        if self.last_biome is None:
            self.last_biome = biome
            firstTime = True

        if firstTime:
            description = f'Private Server:\n{self.pslink}'

            embed1 = {
                'title': f'Current Biome: {biome}',
                'description': description,
                'footer': {'text': self.data['Version']},
                'color': self.biomedata[biome]['color'],
                'thumbnail': {
                    'url': self.biomedata[biome]['image']
                }
            }

            embeds.append(embed1)

            payload['embeds'] = embeds

            for hook in self.data['Webhooks'].values():
                response = requests.post(hook, json=payload)

                if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                    print('Error encountered while requests.post, attempting to use default values to send...')
                    payload.pop('avatar_url')

                    response = requests.post(hook, json=payload)

                

                if 200 <= response.status_code < 300:
                    pass
                elif str(response.status_code)[0] == '4':
                    print('Still failed, pls open an issue')
                else:
                    print('Unexpected response — possibly invalid avatar URL or other issue')

        elif biome != self.last_biome:
            updateCounter = True
            description = f'Private Server:\n{self.pslink}' if biome != 'NORMAL' else ''
            title = f'Biome {"Ended" if biome == "NORMAL" else "Started"} | {self.last_biome if biome == "NORMAL" else biome}'

            embed1 = {
                'title': title,
                'description': description,
                'footer': {'text': self.data['Version']},
                'color': self.biomedata[biome if biome != 'NORMAL' else self.last_biome]['color'],
                'thumbnail': {
                    'url': self.biomedata[biome]['image']
                }
            }

            fields = [
                {
                    'name': 'Current Aura',
                    'value': aura,
                    'inline': True
                }
            ]

            if biome != 'NORMAL':
                fields = [
                    {
                        'name': 'Biome Found at',
                        'value': discord_time,
                        'inline': True
                    },
                    {
                        'name': 'Biome Ending in',
                        'value': f'<t:{timestamp + self.biomedata[biome]["duration"]}:R>' if isinstance(self.biomedata[biome]["duration"], int) else '**NOT FOUND**',
                        'inline': True
                    },
                ] + fields

            embed1['fields'] = fields


            if self.last_biome != 'NORMAL' and biome != 'NORMAL':
                embed2 = {
                    'title': f'Biome Replaced | {self.last_biome}',
                    'color': self.biomedata[self.last_biome]['color']
                }

                embeds.append(embed2)

            embeds.append(embed1)

            payload['embeds'] = embeds
            

            for hook in self.data['Webhooks'].values():
                response = requests.post(hook, json=payload)
                self.appendlogs(f'[LINE 291 IN CODE, LINE {self.last_position} IN LOGFILE] Message sent with status code {response.status_code} at {self.current_time}')

                if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                    print('Error encountered while requests.post, attempting to use default values to send...')
                    payload.pop('avatar_url')

                    response = requests.post(hook, json=payload)

                if 200 <= response.status_code < 300:
                    pass
                elif str(response.status_code)[0] == '4':
                    print('Still failed, pls open an issue')
                else:
                    print('Unexpected response — possibly invalid avatar URL or other issue')

            
        if updateCounter:
            self.appendlogs(f'[LINE 295 IN CODE, LINE {self.last_position} IN LOGFILE] {biome} detected at {self.current_time}.')

        if 'on_biome' in self.events:
            await self.events['on_biome'](biome, aura, updateCounter=updateCounter)

        self.last_biome = biome

        if __name__ == '__main__':
            print(f'Biome: {biome}')

    # main loop
    async def run(self):
        timestamp = int(time.time())
        discord_time = f"<t:{timestamp}:R>"

        if 'get_data' in self.events:
            self.data = await self.events['get_data']()

        if 'RobloxPlayerBeta.exe' not in [proc.info['name'] for proc in psutil.process_iter(['pid', 'name'])]:
            self.blacklisted_files.append(self.get_latest_log_file())

            try:
                os.startfile(self.convert_roblox_link(self.data['Server']))

            except Exception as e:
                self.appendlogs(f'Exception: [{e}] has occured.')
                print(f'EXCEPTION CAPTURED! Check logfile {self.currentLog} for more info')

        payload = {
            'username': self.data['webhook_name'],
            'avatar_url': self.data['webhook_avatar'],
            'embeds': [
                {
                    'title': f'Macro Started',
                    'description': 'The macro has started running!',
                    'footer': {'text': self.data['Version']},
                    'color': 0x00FF00
                }
            ]
        }

        for hook in self.data['Webhooks'].values():
            response = requests.post(hook, json=payload)
            self.appendlogs(f'[LINE 291 IN CODE, LINE {self.last_position} IN LOGFILE] Message sent with status code {response.status_code} at {self.current_time}')

            if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                print('Error encountered while requests.post, attempting to use default values to send...')
                payload.pop('avatar_url')

                response = requests.post(hook, json=payload)

            if 200 <= response.status_code < 300:
                pass
            elif str(response.status_code)[0] == '4':
                print('Still failed, pls open an issue')
            else:
                print('Unexpected response — possibly invalid avatar URL or other issue')

            
        while True:
            self.current_time = datetime.now().strftime('%Y-%m-%d %H:%M.%S')

            if __name__ != '__main__':
                if 'get_data' in self.events:
                    self.data = await self.events['get_data']()

                if not self.data['active']: return

                if self.data['sendLogs']:
                    await self.check_biome()

            elif __name__ == '__main__':
                await self.check_biome()

            await asyncio.sleep(1)
