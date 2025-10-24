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
from datetime import datetime, timezone

from tkinter import messagebox as mb

import pygame
from windows_toasts import *

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

def show_toast(field, function):
    toast = Toast(
        text_fields=[field],
        on_activated=function
    )
    
    self.toaster.show_toast(toast)

def push_window():
    hwnd = win32gui.FindWindow(None, 'Roblox')

    try:
        if hwnd != 0:
            win32gui.SetForegroundWindow(hwnd)
        else:
            time.sleep(15 * 60)

    except Exception as e:
        keyboard.send('shift')

        if hwnd != 0:
            win32gui.SetForegroundWindow(hwnd)
        else:
            time.sleep(15 * 60)

# class
class LogSniper:
    def __init__(self, data, mixer=False, toaster=WindowsToaster('Macro Alert')):
        self.data = data

        self.path = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox', 'logs')
        self.events = {}
        self.sendLogs = True

        self.webhooks = [hook for hook in self.data['Webhooks'].values()]
        self.pslink = data['Server']

        self.current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.currentLog = f'logs/{self.current_time}-logger-log'

        self.macro_start_time = 0

        self.biomedata = requests.get(data['PresetData']).json()

        self.toaster = toaster

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

        if not mixer:
            pygame.mixer.init()

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

    def format_time(self, seconds):
        seconds = int(seconds)
        
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}h {m}m {s}s"

    def on_shutdown(self, biomes_found):
        timestamp = int(time.time())
        discord_time = f"<t:{timestamp}:R>"

        session_length = self.format_time(timestamp - self.macro_start_time)

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

        # biomes
        biome_text = ''
        total_biomes = sum(self.data['biomes_found'].values())
        
        biomes = {elm: self.data['biomes_found'][elm] for elm in sorted(self.data['biomes_found'], key=lambda k: self.data['biomes_found'][k], reverse=True)}
        for biome, val in biomes.items():
            biome_text += f'{biome}: {val}\n'

        biome_text = 'None' if biome_text == '' else biome_text.strip('\n')
        
        # merchants
        merchant_text = ''
        total_merchants = sum(self.data['merchants_found'].values())

        merchants = {elm: self.data['merchants_found'][elm] for elm in sorted(self.data['merchants_found'], key=lambda k: self.data['merchants_found'][k], reverse=True)}

        for merchant, val in merchants.items():
            merchant_text += f'{merchant}: {val}\n'

        merchant_text = 'None' if merchant_text == '' else merchant_text.strip('\n')

        fields = [
            {
                'name': 'Session Length',
                'value': session_length,
                'inline': True
            },
            {
                'name': f'Biomes found this session ({total_biomes})',
                'value': biome_text,
                'inline': False
            },
            {
                'name': f'Merchants found this session ({total_merchants})',
                'value': merchant_text,
                'inline': False
            },
        ]

        payload['embeds'][0]['fields'] = fields

        for hook in self.data['Webhooks'].values():
            response = requests.post(hook, json=payload)

            if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                print(f'[LINE 251] Error encountered while requests.post, attempting to use default values to send...\nResponse code:{response.status_code}')
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

    async def merchant_detected(self, merchant, line, timestamp):
        print(f'[DEBUG] LINE:\n{line}')
        merchant_spawntime = line.split(',')[0]

        dt = datetime.strptime(merchant_spawntime, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=timezone.utc)
        print(f'[DEBUG] DT:\n{dt}')

        merchant_timestamp = int(dt.timestamp())
        merchant_remaining_time = self.biomedata["merchants"][merchant]["duration"]
        print(f'[DEBUG] MERCHANT TIMESTAMP:\n{merchant_timestamp}\n\n')
        
        if timestamp >= merchant_timestamp + 5: return # +5 is tolerance, write any logic below this line

        if merchant == 'Eden':
            if os.path.isfile(self.data['Rare Merchant Sound']):
                pygame.mixer.music.load(self.data['Rare Merchant Sound'])
                pygame.mixer.music.play()
                
            else:
                print("[RARE MERCHANT] ⚠️ Sound file not found.")

        if 'on_merchant' in self.events:
            await self.events['on_merchant'](merchant)
        
        payload = {
            'username': self.data['webhook_name'] + ' | Merchants',
            'avatar_url': self.data['webhook_avatar']
        }

        payload['content'] = f'<@{(await self.events["get_discord_data"]()).user.id}>' if merchant == 'Eden' else ''

        # embeds --------------------------------------------------
        embeds = []

        discord_time = f"<t:{merchant_timestamp}:F>"

        embed1 = {
            'title': f'{merchant} Found!',
            'description': f'Private Server:\n{self.pslink}',
            'footer': {'text': self.data['Version']},
            'fields': [
                {
                    'name': 'Merchant Spawned at',
                    'value': discord_time,
                    'inline': True
                },
                {
                    'name': 'Merchant Leaving / Left',
                    'value': f'<t:{merchant_timestamp + merchant_remaining_time}:R>' if isinstance(self.biomedata["merchants"][merchant]["duration"], int) else '**NOT FOUND**',
                    'inline': True
                },
            ],
            'color': self.biomedata['merchants'][merchant]['color']
        }

        embeds.append(embed1)

        payload['embeds'] = embeds

        for hook in self.data['Webhooks'].values():
            response = requests.post(hook, json=payload)
            
            if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                print(f'[LINE 331] Error encountered while requests.post, attempting to use default values to send...\nResponse code:{response.status_code}')
                payload.pop('avatar_url')

                response = requests.post(hook, json=payload)

            if 200 <= response.status_code < 300:
                pass
            elif str(response.status_code)[0] == '4':
                print('Still failed, pls open an issue')
            else:
                print('Unexpected response — possibly invalid avatar URL or other issue')

    async def perform_checks(self):
        logpath = self.get_latest_log_file()
        log_lines = self.read_logfile(logpath)

        if not log_lines:
            return

        await self.check_biome(log_lines)
        await self.check_merchant(log_lines)

    async def check_merchant(self, log_lines):
        for line in reversed(log_lines):
            if 'Incoming MessageReceived Status' in line:
                timestamp = int(time.time())
                
                match = {
                    "[Merchant]: Mari has arrived on the island...": lambda l, t: self.merchant_detected('Mari', l, t),
                    "<font color=\"#a352ff\">[Merchant]: Jester has arrived on the island!!</font>": lambda l, t: self.merchant_detected('Jester', l, t),
                    ("Eden has appeared", "<"): lambda l, t: self.merchant_detected('Eden', l, t),
                }

                if "&lt;" in line:
                    continue

                for match, action in match.items():
                    if isinstance(match, tuple):
                        if all(m in line for m in match):
                            await action(line, timestamp)
                            return
                    else:
                        if match in line:
                            await action(line, timestamp)
                            return

    async def check_biome(self, log_lines): # this function calls read logs and get latest already
        if not log_lines:
            return

        for line in reversed(log_lines):
            if '[FLog::Output]' in line:
                matchstring = r'\[BloxstrapRPC\] (.*)'

                match = re.search(matchstring, line) # fnc search to find stuff in mid

                if match:
                    match = match.group(1)
                else:
                    continue

                fixed = re.sub(r'"state":"Equipped "([^"]+)"', r'"state":"Equipped \"\1\""', match)

                data = json.loads(fixed)

                state = data["data"]["state"]
                
                aura = state.replace('Equipped ', '').strip('_').replace('_', ' ').strip('"')
                biome = data["data"]["largeImage"]["hoverText"]

                await self.biomedetected(biome, aura)
                return

    # async methods
    async def biomedetected(self, biome, aura):
        if biome not in self.biomedata: return
        aura = 'Loading...' if aura.lower() == 'in main menu' else aura

        self.last_aura = aura

        firstTime = self.last_biome is None
        updateCounter = False
        payload = {
            'username': self.data['webhook_name'] + ' | Biomes',
            'content': '',
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
            firstTime = True
        
        if biome in self.biomedata and self.last_biome != biome:
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
                self.last_biome = biome
                        
            elif self.last_biome != biome:
                if biome in (self.biomedata['glitch_keywords'] + self.biomedata['dream_keywords']):
                    payload['content'] = '@everyone'

                    if os.path.isfile(self.data['Rare Biome Sound']):
                        pygame.mixer.music.load(self.data['Rare Biome Sound'])
                        pygame.mixer.music.play()
                        
                    else:
                        print("[RARE BIOME] ⚠️ Sound file not found.")

                    show_toast(f'{biome.upper()} has been found in your server!', lambda _: push_window())

                updateCounter = (True if biome != 'NORMAL' else False)
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
                    if ('duration' not in self.biomedata[biome] or self.biomedata[biome]['duration'] is None) and 'fetch_biome_data' in self.events:
                        await self.events['fetch_biome_data']()
                    
                    fields = [
                        {
                            'name': 'Biome Found at',
                            'value': discord_time,
                            'inline': True
                        },
                        {
                            'name': 'Biome Ending / Ended',
                            'value': f'<t:{timestamp + self.biomedata[biome]["duration"]}:R>' if isinstance(self.biomedata[biome]["duration"], int) else self.biomedata[biome]["duration"] if self.biomedata[biome]["duration"] != None else '**NOT FOUND**',
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
                    print(f'[LINE 527] Error encountered while requests.post, attempting to use default values to send...\nResponse code:{response.status_code}')
                    payload.pop('avatar_url')

                    response = requests.post(hook, json=payload)

                if 200 <= response.status_code < 300:
                    pass
                elif str(response.status_code)[0] == '4':
                    print('Still failed, pls open an issue')
                else:
                    print('Unexpected response — possibly invalid avatar URL or other issue')


        '''elif biome not in self.biomedata:
            if firstTime:
                pass
            
            else:
                updateCounter = True
                description = f'Private Server:\n{self.pslink}'
                title = f'Biome Started | {biome}'

                embed1 = {
                    'title': title,
                    'description': description,
                    'footer': {'text': self.data['Version']},
                    'color': 5879591,
                    #'thumbnail': {'url': self.biomedata[biome]['image']}
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
                            'name': 'Biome Ending / Ended',
                            'value': '**NOT FOUND**',
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
                    print(f'Error encountered while requests.post, attempting to use default values to send...\nResponse code:{response.status_code}')
                    payload.pop('avatar_url')

                    response = requests.post(hook, json=payload)

                if 200 <= response.status_code < 300:
                    pass
                elif str(response.status_code)[0] == '4':
                    print('Still failed, pls open an issue')
                else:
                    print('Unexpected response — possibly invalid avatar URL or other issue')'''

        if self.last_biome != biome:
            self.appendlogs(f'[LINE 295 IN CODE, LINE {self.last_position} IN LOGFILE] {biome} detected at {self.current_time}.')

        if 'on_biome' in self.events:
            await self.events['on_biome'](biome, aura, updateCounter=updateCounter)

        self.last_biome = biome

        if __name__ == '__main__':
            print(f'Biome: {biome}')

    # main loop
    async def run(self):
        self.macro_start_time = int(time.time())
        timestamp = int(time.time())
        discord_time = f"<t:{timestamp}:R>"

        if 'get_data' in self.events:
            self.data = await self.events['get_data']()

        if not os.path.exists(os.path.join(os.getenv('LOCALAPPDATA'), 'Bloxstrap')):
            mb.showwarning('Please download bloxstrap', 'Bloxstrap isnt downloaded, unable to snipe merchant.\nIf you don\'t want to merchant snipe, please close and ignore this warning')

        else:
            '''
            fflags = {}
            
            with open(os.path.join(os.getenv('LOCALAPPDATA'), 'Bloxstrap', 'Modifications', 'ClientSettings', 'ClientAppSettings.json'), 'r') as f:
                fflags = json.load(f)

            targetitems = {
                'FStringDebugLuaLogLevel': 'trace',
                'FStringDebugLuaLogPattern': 'ExpChat/mountClientApp'
            }

            if not all(fflags.get(k) == v for k, v in targetitems.items()):
                fflags.update(targetitems)
                
            with open(os.path.join(os.getenv('LOCALAPPDATA'), 'Bloxstrap', 'Modifications', 'ClientSettings', 'ClientAppSettings.json'), 'w') as f:
                json.dump(fflags, f)
                print('Missing FFlags updated')
            '''

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
                print(f'[LINE 681] Error encountered while requests.post, attempting to use default values to send...\nResponse code:{response.status_code}')
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
                    await self.perform_checks()

            elif __name__ == '__main__':
                await self.perform_checks()

            await asyncio.sleep(1)
