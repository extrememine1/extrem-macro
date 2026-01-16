import random
import re
import os
import json
import requests

import asyncio
import threading

import selfcord
from selfcord.ext import commands

import pygame
from tkinter import messagebox as mb

from windows_toasts import *

from datetime import datetime

# local variables
url_pattern = re.compile(r'https?://[^\s]+')
game_pattern = r"https:\/\/www\.roblox\.com\/games\/(\d+)\/[^?]+\?privateServerLinkCode=(\d+)"
share_pattern = r"https:\/\/www\.roblox\.com\/share\?code=([a-f0-9]+)&type=([A-Za-z]+)"

# main class
class MyClient(commands.Bot):
    def __init__(self, imports, toaster=WindowsToaster('Macro Alert'), mixer=False):
        super().__init__(command_prefix="%", self_bot=True)
        self.imports = imports
        
        self.token = imports['Token']
        self.events = {}
        self.toaster = toaster

        self.rarenotif = imports['Rare Biome Sound']
        
        self.blacklist = [
            1271189513619902515,
            1337886908251902114,
            1271189425459826702,
            1290022552105648168,
            1311743706923143258,
            1341135964109803541,
            1358473933804015860,
            1348261847459037255,
            1271190742911684638,
            1311362490575097997,
            1411876944080928849,
            1309940939812503672,
            1309954772635226206
        ]

        self.servers = [1220146999480029224, 1271189425459826699, 1362219755489988646, 1396579777665568868]
        self.cmd_whitelist = imports['cmd_whitelist']

        self.current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.currentLog = f'logs/{self.current_time}-sniper-log'

        self.ready_event = asyncio.Event()
        
        # init funcs
        if not mixer:
            pygame.mixer.init()

        self.biomedata = requests.get(imports['PresetData']).json()

        if 'logs' not in os.listdir():
            os.mkdir('logs')

        with open(self.currentLog, 'w', encoding='utf-8') as file:
            file.write('')

    def event(self, coro):
        self.events[coro.__name__] = coro
        return coro

    async def proc_commands_for_others(self, message):
        content = message.content
        
        if not content.startswith(self.command_prefix): return

        parts = content[len(self.command_prefix):].strip().split()

        if not parts: return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ['system_command', 'is_my_pc_going_to_explode']: return

        for command in self.commands:
            if command.name == cmd:
                if args:
                    await command.callback(message, *args)
                    
                else:
                    await command.callback(message)
    
    async def on_ready(self):
        print('Logged on as', self.user)

        self.ready_event.set()

    async def on_message(self, message):
        self.current_time = datetime.now().strftime('%Y-%m-%d %H:%M.%S')
        
        if message.guild and message.guild.id in self.servers and message.channel and message.channel.id not in self.blacklist:
            self.appendlogs(f'Message detected in {message.channel.name} at {self.current_time}')
            await self.notifLink(message)

            if 'on_glitch' in self.events:
                await self.events['on_glitch'](message) # PORT

        if message.author.id == self.user.id:
            await self.process_commands(message)
            
        elif message.author.id in self.cmd_whitelist:
            await self.proc_commands_for_others(message)

    def appendlogs(self, message):
        with open(self.currentLog, 'a', encoding='utf-8') as file:
            file.write(f'{message}\n')

    # local functions
    def convert_roblox_link(self, url): # credits to dan and yeswe
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

    async def check(self, message):
        rare_found = False
        deep_link = None
        biome = None
        own_link = False

        # rework this system to parameter based

        def detect_biome(text):
            for biom in self.biomedata['rare_biomes']:
                if biom in text:
                    return biom
            return None

        text_fields = [message.content] + [
            text
            for sublist in [[embed.title, embed.description]
                            for embed in message.embeds
                            ]
            
            for text in sublist
        ]

        for embed in message.embeds:
            if hasattr(embed, 'fields'):
                text_fields += [field.value for field in embed.fields]

        text_fields = [text for text in text_fields if type(text) == str]

        link_matches = [url_pattern.search(text) for text in text_fields]
        if any(link_matches):
            link_match = [x for x in link_matches if x != None][0]
            deep_link = self.convert_roblox_link(link_match.group())

        biomes = [detect_biome(text) for text in text_fields] # None if no rare biome else str
        if any(biomes):
            biome = [x for x in biomes if x != None][0]
            rare_found = True

        for text in text_fields:
            if self.imports['Server'] in text:
                own_link = True

        if rare_found:
            self.imports = await self.events['get_data']()
            self.rarenotif = self.imports['Rare Biome Sound'] or r'sounds/glitchNotif.mp3'

        return biome, rare_found, deep_link, own_link
        #      str    bool        str        bool


    async def notifLink(self, message):
        biome, rare_found, deep_link, own_link = await self.check(message)

        def show_toast():
            toast = Toast(
                text_fields=[f'{biome.upper()} found in {message.channel.name}'],
                on_activated=lambda _: (asyncio.create_task(self.events['rareSniped'](biome)), os.startfile(deep_link))
            )
            self.toaster.show_toast(toast)

        if deep_link and rare_found:
            if not own_link:
                if os.path.isfile(self.rarenotif):
                    pygame.mixer.music.load(self.rarenotif)
                    pygame.mixer.music.play()
                    
                else:
                    print("[RARE BIOME] ⚠️ Sound file not found.")

                self.appendlogs(f"Deep link is: {deep_link!r}")

                threading.Thread(target=show_toast, daemon=True).start()

            else:
                print(f'[DISC SNIPER] {biome.upper()} detected in own server, logsniper will do the alerting')
