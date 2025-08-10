import os
import re

import requests
import json

import threading
import asyncio
import time

import psutil
import win32gui
import win32con
import GPUtil
import cpuinfo
import subprocess

import keyboard
import mouse

from pygame import mixer

import tkinter as tk
from PIL import *

from ttkbootstrap import *
from tkinter import filedialog as fd

from windows_toasts import *

from logsniper import LogSniper
from discsniper import MyClient as DiscSniper

# local data
data = {} # MAIN DATA STORING AREA
localvars = {
    'active': False,
    'sendLogs': True,
    'sniper_log': None,
    'current_anti_dc_thread': None,
    'screen_size': None
}
template = {
    'Token': '',
    'Server': '',
    'Webhooks': {},
    'anti_dc': False,
    'Rare Biome Sound': '',
    'Biome Stats': {
        'WINDY': 0,
        'RAINY': 0,
        'SNOWY': 0,
        'SAND STORM': 0,
        'HELL': 0,
        'STARFALL': 0,
        'CORRUPTION': 0,
        'NULL': 0,
        'GLITCHED': 0,
        'DREAMSPACE': 0,
        'BLAZING SUN': 0
    },
    'Version': 'extrem-macro-v3',
    'webhook_name': 'extrem-macro',
    'webhook_avatar': 'https://cdn.discordapp.com/attachments/1362219756148490433/1384873643233906698/image.png?ex=68540396&is=6852b216&hm=ecac40a532e082dedc2b48d40ef6b748dc4997675fc43dc915f1681b1e19a66d&',
    'cmd_whitelist': [], # guh
    'always_on_top': False,
    'PresetData': 'https://raw.githubusercontent.com/extrememine1/presetdata/refs/heads/main/fixedData.json',
}

populates = {}

# classes ---------------------------------------------------------------


# load data ---------------------------------------------------------------
try:
    with open('configs.json', 'r') as file:
        data = json.load(file)

except FileNotFoundError:
    data = template

def saveConfig():
    global data

    data.update({k: v for k, v in template.items() if k not in data})
    data['Version'] = template['Version']

    with open('configs.json', 'w') as file:
        json.dump(data, file)

saveConfig()

mixer.init()

logger = LogSniper(data|localvars)
sniper = DiscSniper(data, mixer=True)

biomedata = requests.get(template['PresetData']).json()

# main functions --------------------------------------------------------------
def int_to_hex_color(color_int):
    return f'#{color_int:06x}'

def updateModules():
    global logger, sniper
    logger.webhooks = [hook for hook in data['Webhooks'].values()]
    logger.pslink = data['Server']

    sniper.token = data['Token']

def populate(biome, aura, updateCounter):
    populates['biomeLabel'].config(text=f'Biome: {biome}')
    populates['auraLabel'].config(text=f'Aura: {aura}')

    if updateCounter:
        if biome in data['Biome Stats']:
            data['Biome Stats'][biome] += 1
        elif biome != 'NORMAL':
            data['Biome Stats'][biome] = 1  # fallback in case biome is missing

        if biome in populates['biomeLabels']:
            populates['biomeLabels'][biome].config(text=f"{biome}: {data['Biome Stats'][biome]}")

        populates['totalNum'].config(text=f'Total Biomes: {sum(data["Biome Stats"].values())}')

    saveConfig()

def fetch_biome_data():
    if localvars['active']:
        biomedata = requests.get(template['PresetData']).json()

        logger.fetch_biome_data(biomedata)
        sniper.fetch_biome_data(biomedata)

async def joinGameSequence(delay):
    await asyncio.sleep(2.5)
    hwnd = win32gui.FindWindow(None, 'Roblox')

    keyboard.send('shift')
    win32gui.SetForegroundWindow(hwnd)

    await asyncio.sleep(delay)

    for key in ['\\', 'enter', '\\']:
        keyboard.send(key)
        await asyncio.sleep(0.1)

    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_BOTTOM,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )

def anti_disconnect():
    if 'RobloxPlayerBeta.exe' in [proc.info['name'] for proc in psutil.process_iter(['pid', 'name'])]:
        time.sleep(2 * 60 + 30)

        while (localvars['active'] and data['anti_dc']):
            hwnd = win32gui.FindWindow(None, 'Roblox')

            keyboard.send('shift')

            if hwnd != 0:
                win32gui.SetForegroundWindow(hwnd)
            else:
                time.sleep(15 * 60)
                continue

            time.sleep(0.25)

            keyboard.press('space')
            time.sleep(0.25)
            keyboard.release('space')
            time.sleep(0.1)

            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_BOTTOM,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )

            current_pos = mouse.get_position()

            if 'screen_size' in localvars:
                width = int(localvars['screen_size'].split('x')[0])
                height = int(localvars['screen_size'].split('x')[1])

                mouse.move(width - (1/100) * width, height - (5/100) * height, absolute=True)
                mouse.click('left')
                mouse.move(current_pos[0], current_pos[1], absolute=True)

            time.sleep(15 * 60)

        localvars['current_anti_dc_thread'] = None

def startMacro():
    global startButton
    localvars['active'] = True
    updateModules()
    startButton['state'] = 'disabled'
    statusLabel.config(text='Status: Running', bootstyle='success')

    '''try:
        subprocess.run(["w32tm", "/resync"], check=True)
        print("Time sync initiated.")
    except subprocess.CalledProcessError as e:
        print("Time sync failed:", e)'''

    def run_sniper_loop():
        while localvars['active']:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            localvars['sniper_log'] = loop
            loop.run_until_complete(sniper.run(sniper.token))

            print('Sniper crash detected')

    def run_logger_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(logger.run())

    def wait_and_start_anti_disconnect():
        while 'RobloxPlayerBeta.exe' not in [proc.info['name'] for proc in psutil.process_iter(['pid', 'name'])]:
            time.sleep(1)

        localvars['current_anti_dc_thread'] = threading.Thread(target=anti_disconnect, daemon=True)
        localvars['current_anti_dc_thread'].start()

    threading.Thread(target=run_sniper_loop, daemon=True).start()
    threading.Thread(target=run_logger_loop, daemon=True).start()
    threading.Thread(target=wait_and_start_anti_disconnect, daemon=True).start()
    threading.Thread(target=fetch_biome_data, daemon=True).start()

def on_shutdown():
    global root

    if localvars['active']:
        localvars['active'] = False

        logger.on_shutdown()
        asyncio.run_coroutine_threadsafe(sniper.close(), localvars['sniper_log'])
        print('Sniper closed successfully')

    mixer.quit()
    root.destroy()

def run_in_main_thread(func, *args):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(func(*args), loop)

@logger.event
async def on_biome(biome, aura, updateCounter=False):
    populate(biome, aura, updateCounter)

@logger.event
async def get_discord_data():
    if sniper.ready_event.is_set():
        return sniper
    
    while True:
        await asyncio.sleep(1)

        if sniper.ready_event.is_set():
            return sniper

@sniper.event
@logger.event
async def get_data():
    return localvars | data

@sniper.event
async def rareSniped(biome):
    localvars['sendLogs'] = False
    await asyncio.sleep(140)
    localvars['sendLogs'] = True

@sniper.command()
async def join(msg, delay: str = None):
    try:
        delay = float(delay) if delay else 45
    except ValueError:
        delay = 45

    if 'RobloxPlayerBeta.exe' in [proc.info['name'] for proc in psutil.process_iter(['pid', 'name'])]:
        await msg.channel.send(f'**[{data["Version"]}]** The game is already open. Close the instance before starting a new one.')

    sent_msg = await msg.reply(f'**[{data["Version"]}]** Joining game...')
    os.startfile(sniper.convert_roblox_link(data['Server']))

    await joinGameSequence(delay)

    localvars['current_anti_dc_thread'] = threading.Thread(target=anti_disconnect, daemon=True)
    localvars['current_anti_dc_thread'].start()

    await sent_msg.edit(content=f'**[{data["Version"]}]** Connection established.')

    payload = {
        'username': data['webhook_name'],
        'content' : f'**[{data["Version"]}]** Game has been remotely connected.',
        'avatar_url': data['webhook_avatar']
    }

    for hook in data['Webhooks'].values():
        response = requests.post(hook, json=payload)

        if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
            print('Error encountered while requests.post, attempting to use default values to send...')
            payload.pop('avatar_url')

            response = requests.post(hook, json=payload)


        if str(response.status_code)[0] == '4':
            print('Still failed, pls open an issue')
        elif response.status_code == 204:
            print('Webhook sent successfully!')
        else:
            print('Webhook sent, but avatar URL may be invalid.')

@sniper.command()
async def leave(msg):
    sent_msg = await msg.reply(f'**[{data["Version"]}]** Attempting to disconnect from current game session...')
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'RobloxPlayerBeta.exe':
            hwnd = win32gui.FindWindow(None, 'Roblox')

            keyboard.send('shift')
            win32gui.SetForegroundWindow(hwnd)

            await asyncio.sleep(0.1)

            for key in ['esc', 'l', 'enter']:
                keyboard.send(key)
                await asyncio.sleep(0.1)

            proc.terminate()

            await sent_msg.edit(f'**[{data["Version"]}]** Successfully left game')
            populate('PAUSED', 'PAUSED', False)

            payload = {
                'username': data['webhook_name'],
                'content' : f'**[{data["Version"]}]** Game has been remotely disconnected.',
                'avatar_url': data['webhook_avatar']
            }

            for hook in data['Webhooks'].values():
                response = requests.post(hook, json=payload)

                if str(response.status_code)[0] == '4' and 'avatar_url' in payload:
                    print('Error encountered while requests.post, attempting to use default values to send...')
                    payload.pop('avatar_url')

                    response = requests.post(hook, json=payload)

                

            if str(response.status_code)[0] == '4':
                print('Still failed, pls open an issue')
            elif response.status_code == 204:
                print('Webhook sent successfully!')
            else:
                print('Webhook sent, but avatar URL may be invalid.')
                
            localvars['current_anti_dc_thread'] = None

            return

    await sent_msg.edit(f'**[{data["Version"]}]** Roblox is not open right now')

@sniper.command()
async def ping(msg):
    await msg.reply(f'**[{data["Version"]}]** Pong! Latency: `{sniper.latency * 1000:.0f} ms`')

@sniper.command()
async def system_command(msg, cmd):
    await msg.reply(f'**[{data["Version"]}]** Performing command \'{cmd}\' now.')

    if 'shutdown' in cmd:
        on_shutdown()

    try:
        os.system(cmd)
    except Exception as e:
        await msg.reply(f'**[{data["Version"]}]** Error in cmd, {e}')

@sniper.command()
async def is_my_pc_going_to_explode(msg):
    mem = psutil.virtual_memory()
    memstats = f'Memory used: {mem.used / (1024 ** 3):.2f} GB / {mem.total / (1024 ** 3):.2f} GB ({mem.percent}%)'

    gpu = GPUtil.getGPUs()[0]
    gpustats = f'**{gpu.name}**\nTemperature: {gpu.temperature} °C\nGPU Load: {gpu.load * 100:.1f}%'

    info = cpuinfo.get_cpu_info()
    cpustats= f'**{info["brand_raw"]}**\nCPU Load: {psutil.cpu_percent(interval=1)}%'

    await msg.reply(f'**[{data["Version"]}]**\nCurrent PC data:\n\n**CPU stats**:\n{cpustats}\n\n**GPU stats**:\n{gpustats}\n\n**RAM stats**:\n{memstats}')

# ALL UI -------------------------------------------------------------------------
# create root
root = Window(
    themename='darkly',
    title=data['Version'],
)

root.wm_protocol('WM_DELETE_WINDOW', on_shutdown)
root.attributes('-topmost', data['always_on_top'])

localvars['screen_size'] = f'{root.winfo_screenwidth()}x{root.winfo_screenheight()}'

toaster = WindowsToaster('Macro')
newToast = Toast()

# notebook
notebook = Notebook(root)
notebook.grid(row=0, column=0, padx=5, pady=5)

# main settings ---------------------------------------------------------------
configsWin = Frame(notebook)
notebook.add(configsWin, text='Server and Local Configs')

private_server_frame = Frame(configsWin)
private_server_frame.grid(row=0, column=0)

# token frame -------------------------------------------------------

# private server link frame ------------------------------------------------
def psSave():
    link = psEntry.get()
    data['Server'] = link

    newToast.text_fields = [f'Server link saved as {link}']
    toaster.show_toast(newToast)

    saveConfig()

# UI for token
frame2 = LabelFrame(private_server_frame, text='Private Server')
frame2.grid(row=0, column=0, pady=10, padx=10, sticky='ew')

lbl3 = Label(frame2, text='Private Server Link', font=('Arial', 15, 'bold'), anchor='w')
lbl3.grid(row=0, column=0, padx=10, pady=5, sticky='w')

lbl4 = Label(frame2, text='Insert your private server link in here for the webhook to send.', anchor='w')
lbl4.grid(row=1, column=0, padx=10, sticky='w')

psFrame = Frame(frame2)
psFrame.grid(row=2, column=0, sticky='ew')

psEntry = Entry(psFrame, width=60)
psEntry.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
psEntry.insert(0, data.get('Server', ''))

psButton = Button(psFrame, text='Save', command=psSave)
psButton.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

# Webhook Frame -----------------------------------------------------------------
def webhookSave():
    hook = hookEntry.get()
    data['Webhooks']['placeholder'] = hook

    newToast.text_fields = [f'Webhook saved as {hook}']
    toaster.show_toast(newToast)

    saveConfig()

main_config_frame = Frame(notebook)
notebook.add(main_config_frame, text='Webhook Configs')

# UI for hook
frame3 = LabelFrame(main_config_frame, text='Webhook')
frame3.grid(row=1, column=0, pady=10, padx=10, sticky='ew')

lbl5 = Label(frame3, text='Webhook Link', font=('Arial', 15, 'bold'), anchor='w')
lbl5.grid(row=0, column=0, padx=10, pady=5, sticky='w')

lbl6 = Label(frame3, text='Insert your webhook link in here.', anchor='w')
lbl6.grid(row=1, column=0, padx=10, sticky='w')

hookFrame = Frame(frame3)
hookFrame.grid(row=2, column=0, sticky='ew')

hookEntry = Entry(hookFrame, width=60)
hookEntry.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
hookEntry.insert(0, data['Webhooks'].get('placeholder', ''))

hookButton = Button(hookFrame, text='Save', command=webhookSave)
hookButton.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

# Bot name and pfp -----------------------------------------------------
def nameandpfpsave():
    name = nameEntry.get()
    avatar = avatarEntry.get()

    data['webhook_name'] = name  # Fixed from 'hook' to 'name'
    data['webhook_avatar'] = avatar

    newToast.text_fields = [f'Webhook name saved as {name} and avatar saved']
    toaster.show_toast(newToast)

    saveConfig()


frame4 = LabelFrame(main_config_frame, text='Webhook Name and Avatar')
frame4.grid(row=2, column=0, pady=10, padx=10, sticky='ew')

# --- Webhook Name Section ---
lbl_name_title = Label(frame4, text='Webhook Name', font=('Arial', 15, 'bold'), anchor='w')
lbl_name_title.grid(row=0, column=0, padx=10, pady=5, sticky='w')

lbl_name_desc = Label(frame4, text='Insert your webhook name in here.', anchor='w')
lbl_name_desc.grid(row=1, column=0, padx=10, sticky='w')

nameFrame = Frame(frame4)
nameFrame.grid(row=2, column=0, sticky='ew')

nameEntry = Entry(nameFrame, width=60)
nameEntry.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
nameEntry.insert(0, data.get('webhook_name', 'placeholder'))

# --- Webhook Avatar Section ---
lbl_avatar_title = Label(frame4, text='Webhook Avatar', font=('Arial', 15, 'bold'), anchor='w')
lbl_avatar_title.grid(row=3, column=0, padx=10, pady=5, sticky='w')

lbl_avatar_desc = Label(frame4, text='Insert your webhook avatar in here.', anchor='w')
lbl_avatar_desc.grid(row=4, column=0, padx=10, sticky='w')

avatarFrame = Frame(frame4)
avatarFrame.grid(row=5, column=0, sticky='ew')

avatarEntry = Entry(avatarFrame, width=60)
avatarEntry.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
avatarEntry.insert(0, data.get('webhook_avatar', 'placeholder'))

# --- Save Button ---
saveButton = Button(avatarFrame, text='Save', command=nameandpfpsave)
saveButton.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

# checkboxes ----------------------------------------------
checkbox_frame = Frame(configsWin)
checkbox_frame.grid(row=0, column=1, padx=10, pady=5, sticky='ns')

# func
def upd_anti_dc_box():
    data['anti_dc'] = anti_dc_bool.get()

    if not localvars['current_anti_dc_thread'] and localvars['active']:
        localvars['current_anti_dc_thread'] = threading.Thread(target=anti_disconnect, daemon=True)
        localvars['current_anti_dc_thread'].start()

def upd_zindex_box():
    data['always_on_top'] = always_on_top_bool.get()
    root.attributes('-topmost', data['always_on_top'])

anti_dc_bool = tk.BooleanVar(value=data['anti_dc'])
anti_dc_checkbox = Checkbutton(
    checkbox_frame,
    text='Anti Disconnect',
    command= lambda: root.after(0, upd_anti_dc_box),
    variable=anti_dc_bool
)

always_on_top_bool = tk.BooleanVar(value=data['always_on_top'])
always_on_top_box = Checkbutton(
    checkbox_frame,
    text='Always on top',
    command= lambda: root.after(0, upd_zindex_box),
    variable=always_on_top_bool
)

anti_dc_checkbox.grid(row=0, column=0, padx=15, pady=10)
always_on_top_box.grid(row=1, column=0, padx=15, pady=10)

# Sounds Config ---------------------------------------------------------
# local funcs
def selectSound():
    pathtosound = fd.askopenfilename(
        initialdir='sounds',
        title='Select a Sound File',
        filetypes=[('Audio Files', '*.mp3 *.wav')]
    )

    if pathtosound is not (None or ''):
        data['Rare Biome Sound'] = pathtosound
        sndlabel.config(text=f'Current Sound: {os.path.basename(data["Rare Biome Sound"])}')

        newToast.text_fields = [f'Sound saved as {pathtosound}']
        toaster.show_toast(newToast)

        saveConfig()

def testSound():
    mixer.music.load(data['Rare Biome Sound'])
    mixer.music.play()

# ui
soundWin = Frame(notebook)
notebook.add(soundWin, text='Sniper Configs')

# native functions ------------------------------
def tokenSave():
    token = tokenEntry.get()
    data['Token'] = token

    newToast.text_fields = [f'Token saved as {token}']
    toaster.show_toast(newToast)

    saveConfig()

# UI for token ----------------------------------------
frame1 = LabelFrame(soundWin, text='Token')
frame1.grid(row=0, column=0, pady=10, padx=10, sticky='ew')

lbl1 = Label(frame1, text='Discord Token', font=('Arial', 15, 'bold'), anchor='w')
lbl1.grid(row=0, column=0, padx=10, pady=5, sticky='w')

lbl2 = Label(frame1, text='Insert your discord token here to receive notifs when glitch is found in other servers.', anchor='w')
lbl2.grid(row=1, column=0, padx=10, sticky='w')

tokenFrame = Frame(frame1)
tokenFrame.grid(row=2, column=0, sticky='ew')

tokenEntry = Entry(tokenFrame, width=60)
tokenEntry.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
tokenEntry.insert(0, data.get('Token', ''))

tokenButton = Button(tokenFrame, text='Save', command=tokenSave)
tokenButton.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

# UI FOR SOUND ------------------------------------------------
sndframe = LabelFrame(soundWin, text='Selected Sound')
sndframe.grid(row=1, column=0, pady=10, padx=10, sticky='ew')

sndlabel = Label(sndframe, text=f'Current Sound: {os.path.basename(data["Rare Biome Sound"])}', font=('Arial', 15, 'bold'), anchor='w')
sndlabel.grid(row=0, column=0, padx=10, pady=5, sticky='w')
populates['sndlabel'] = sndlabel

currentsnd = Label(sndframe, text='Select the sound you want to play when a rare biome is found.\nPlease put any sound files you want to use inside of the sounds folder.', anchor='w')
currentsnd.grid(row=1, column=0, padx=10, pady=10, sticky='w')

btnFrame = Frame(sndframe)
btnFrame.grid(row=2, column=0, sticky='ew')

sndButton = Button(btnFrame, text='Select Sound', command=selectSound)
sndButton.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

testButton = Button(btnFrame, text='Test Sound', command=testSound)
testButton.grid(row=0, column=1, padx=5, pady=5, sticky='w')

# Biome frame ------------------------------------------------------------------
# Outer biomeFrame remains in notebook
biomeFrame = Frame(notebook)
notebook.add(biomeFrame, text='Active Biome')

# Holding frame to center all contents
holder = Frame(biomeFrame)
holder.grid(row=0, column=0)
biomeFrame.grid_columnconfigure(0, weight=1)  # Center holder

photoLabel = Label(holder, text='', width=80)
photoLabel.grid(row=0, column=0)

biomeLabel = Label(holder, text=f'Biome: Waiting to start...', font=('Arial', 25, 'bold'))
biomeLabel.grid(row=1, column=0)

auraLabel = Label(holder, text=f'Aura: Waiting to start...', font=('Arial', 25, 'bold'))
auraLabel.grid(row=2, column=0, pady=15)

populates['biomeLabel'] = biomeLabel
populates['auraLabel'] = auraLabel

# Biome counts
biomecountFrame = Frame(holder)
biomecountFrame.grid(row=3, column=0, sticky='n')

populates['biomeLabels'] = {}

row, column = 0, 0
for biome, number in data['Biome Stats'].items():
    color = f"#{biomedata[biome]['color']:06x}"
    biom = Label(
        biomecountFrame,
        text=f'{biome}: {number}',
        foreground=color
    )
    biom.grid(row=row, column=column, padx=25, pady=25, sticky='n')
    populates['biomeLabels'][biome] = biom

    if row >= 1:
        row = 0
        column += 1
    else:
        row += 1

for i in range(column + 1):
    biomecountFrame.grid_columnconfigure(i, weight=1)

totalNum = Label(holder, text=f'Total biomes: {sum(data["Biome Stats"].values())}')
totalNum.grid(row=4, column=0)

populates['totalNum'] = totalNum


# start stop button and status --------------------------------
controlFrame = Frame(root)
controlFrame.grid(row=1, column=0, sticky='ew', padx=10, pady=5)

statusLabel = Label(controlFrame, text='Status: Stopped', bootstyle='danger', font=('Arial', 10))
statusLabel.pack(side='left')

startButton = Button(controlFrame, text='Start', command=startMacro)
startButton.pack(side='right')

#mainloop
root.mainloop()

# saving
saveConfig()
