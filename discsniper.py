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
    def __init__(self, imports, presetdata, toaster=WindowsToaster('Macro Alert'), mixer=False):
        super().__init__(command_prefix="%", self_bot=True)
        self.imports = imports
        
        self.token = imports['Token']
        self.events = {}
        self.toaster = toaster
        self.deep_link = None
        self.rare_found = None

        self.rarenotif = imports['Rare Biome Sound'] or r'sounds/glitchNotif.mp3'
        
        self.blacklist = [
            1271189513619902515, # glitch channel
            1337886908251902114, # dreamscape channel
            1271189425459826702, # jester channel
            1290022552105648168, # void coin channel
            1311743706923143258, # blocked logs channel
            1341135964109803541, # macro application channel
            1358473933804015860, # multi macro application channel
            1348261847459037255, # priv server channel
            1271190742911684638, # general
            1311362490575097997, # catpost
        ]

        self.servers = [1271189425459826699, 1362219755489988646]

        self.current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.currentLog = f'logs/{self.current_time}-sniper-log'

        # init funcs
        if not mixer:
            pygame.mixer.init()

        self.data = presetdata

        if 'logs' not in os.listdir():
            os.mkdir('logs')

        with open(self.currentLog, 'w', encoding='utf-8') as file:
            file.write('')

    def __getitem__(self, key):
        iterable = {
            'Toaster': self.toaster
        }
        
        if key in iterable.keys():
            return iterable[key]
        raise KeyError(key)

    def event(self, coro):
        self.events[coro.__name__] = coro
        return coro
    
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        self.current_time = datetime.now().strftime('%Y-%m-%d %H:%M.%S')
        
        if message.guild and message.guild.id in self.servers and message.channel and message.channel.id not in self.blacklist:
            self.appendlogs(f'Message detected in {message.channel.name} at {self.current_time}')
            await self.notifLink(message)

            if 'on_glitch' in self.events:
                await self.events['on_glitch'](message) # PORT

        if message.author == self.user:
            await self.process_commands(message)

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
        self.rare_found = False
        self.deep_link = None
        biome = None

        def detect_biome(text):
            for kw in self.data['glitch_keywords'] + self.data['dream_keywords']:
                if kw in text:
                    return kw
            return None

        if message.content:
            content_lower = message.content
            found = detect_biome(content_lower)
            if found:
                self.rare_found = True
                biome = found

            link_match = url_pattern.search(message.content)
            if link_match:
                self.deep_link = self.convert_roblox_link(link_match.group())

        for embed in message.embeds:
            if embed.title:
                found = detect_biome(embed.title)
                if found:
                    self.rare_found = True
                    biome = biome or found

            if embed.description:
                desc_lower = embed.description
                found = detect_biome(desc_lower)
                if found:
                    self.rare_found = True
                    biome = biome or found

                link_match = url_pattern.search(embed.description)
                if link_match and not self.deep_link:
                    self.deep_link = self.convert_roblox_link(link_match.group())

            if hasattr(embed, "fields"):
                for field in embed.fields:
                    field_text = f"{field.name} {field.value}"
                    found = detect_biome(field_text)
                    if found:
                        self.rare_found = True
                        biome = biome or found

                    link_match = url_pattern.search(field_text)
                    if link_match and not self.deep_link:
                        self.deep_link = self.convert_roblox_link(link_match.group())

        if self.rare_found:
            self.imports = await self.events['get_data']()
            self.rarenotif = self.imports['Rare Biome Sound'] or r'sounds/glitchNotif.mp3'

        return biome


    async def notifLink(self, message):
        self.deep_link = None
        self.rare_found = False

        biome = await self.check(message)

        def show_toast():
            toast = Toast(
                text_fields=[f'{biome.upper()} found in {message.channel.name}'],
                on_activated=lambda _: (asyncio.create_task(self.events['rareSniped'](biome)), os.startfile(self.deep_link))
            )
            self.toaster.show_toast(toast)

        if self.deep_link and self.rare_found:
            if os.path.isfile(self.rarenotif):
                pygame.mixer.music.load(self.rarenotif)
                pygame.mixer.music.play()
            else:
                print("⚠️ Sound file not found.")

            self.appendlogs(f"Deep link is: {self.deep_link!r}")

            threading.Thread(target=show_toast, daemon=True).start()
