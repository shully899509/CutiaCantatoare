import discord
from discord.ext import commands, tasks
import youtube_dl
import asyncio
import os
import time
import configparser
import sys
import subprocess

from random import choice

discord.opus.load_opus('opus')

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'music.mp3', #%(extractor)s-%(id)s-%(title)s.%(ext)s
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn -y'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options, executable='ffmpeg.exe'), data=data)


client = commands.Bot(command_prefix='?')

status = ['Jamming out to music!', 'Eating!', 'Sleeping!']
queue = []


@client.event
async def on_ready():
    change_status.start()
    print('Bot is online!')


@client.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='general')
    await channel.send(f'Welcome {member.mention}!  Ready to jam out? See `?help` command for details!')


@client.command(name='ping', help='This command returns the latency')
async def ping(ctx):
    await ctx.send(f'**Pong!** Latency: {round(client.latency * 1000)}ms')


@client.command(name='hello', help='This command returns a random welcome message')
async def hello(ctx):
    responses = ['***grumble*** Why did you wake me up?', 'Top of the morning to you lad!', 'Hello, how are you?', 'Hi',
                 '**Wasssuup!**']
    await ctx.send(choice(responses))


@client.command(name='join', help='This command makes the bot join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return

    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()


@client.command(name='queue', help='This command adds a song to the queue')
async def queue_(ctx, url):
    global queue

    queue.append(url)
    await ctx.send(f'`{url}` added to queue!')


@client.command(name='remove', help='This command removes an item from the list')
async def remove(ctx, number):
    global queue

    try:
        del (queue[int(number)])
        await ctx.send(f'Your queue is now `{queue}!`')

    except:
        await ctx.send('Your queue is either **empty** or the index is **out of range**')


@client.command(name='play', help='This command plays songs')
async def play(ctx):
    if os.path.isfile('music.mp3'):
        os.remove('music.mp3')
    if os.path.isfile('music.mp3.part'):
        os.remove('music.mp3.part')

    global queue

    server = ctx.message.guild
    voice_channel = server.voice_client

    async with ctx.typing():
        player = await YTDLSource.from_url(queue[0], loop=client.loop)
        voice_channel.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

    await ctx.send('**Now playing:** {}'.format(player.title))
    del (queue[0])


@client.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.pause()


@client.command(name='resume', help='This command resumes the song!')
async def resume(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.resume()


@client.command(name='view', help='This command shows the queue')
async def view(ctx):
    await ctx.send(f'Your queue is now `{queue}!`')


@client.command(name='leave', help='This command stops makes the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()


@client.command(name='stop', help='This command stops the song!')
async def stop(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.stop()

@client.command(name='next', help='Stop current song and start the next one in queue')
async def next(ctx):
    await(stop(ctx))
    time.sleep(1)
    await(play(ctx))

@tasks.loop(seconds=20)
async def change_status():
    await client.change_presence(activity=discord.Game(choice(status)))

config = configparser.ConfigParser()
config.read('token.ini')
bot_token = config.get('token', 'bot_token')
#print(bot_token)
client.run(bot_token)