# main.py

import functools
from typing import Dict
import asyncio

import discord
from discord.ext import commands
import youtube_dl

from private import token

from queue import Queue

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class Playlist:
    def __init__(self, id: int):
        self.id = id
        self.queue: Queue = Queue(maxsize=0) # maxsize <= 0 means infinite size

    def add_song(self, song: str):
        self.queue.put(song)

    def get_song(self):
        return self.queue.get()

    def empty_playlist(self):
        self.queue.clear()

    @property
    def is_empty(self):
        return self.queue.empty()

    @property
    def track_count(self):
        return self.queue.qsize()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlists: Dict[int, Playlist] = {}

    async def check_play(self, ctx: commands.Context):
        client = ctx.voice_client
        while client and client.is_playing():
            await asyncio.sleep(1)
        
        self.bot.dispatch("track_end", ctx)

    @commands.command()
    async def play(self, ctx: commands.Context, *, url: str):
        if ctx.voice_client is None:
            voice_channel = ctx.author.voice.channel
            if ctx.author.voice is None:
                await ctx.send("`You are not in a voice channel!`")
            if (ctx.author.voice):
                await voice_channel.connect()
        else: 
            pass
        FFMPEG_OPTIONS = {'before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options' : '-vn'}
        YDL_OPTIONS = {'format':'bestaudio', 'default_search':'auto'}

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            if "&list" in url:
                url = url.split("&list")[0]
            info = ydl.extract_info(url, download=False)

            if 'entries' in info:
                url2 = info['entries'][0]['formats'][0]['url']
                title = info['entries'][0]['title']
            elif 'formats' in  info:
                url2 = info['formats'][0]['url']
                title = info['title']
            
            source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
            self.bot.dispatch("play_command", ctx, source, title)

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")
        

    @commands.Cog.listener()
    async def on_play_command(self, ctx: commands.Context, song, title: str):
        playlist = self.playlists.get(ctx.guild.id, Playlist(ctx.guild.id))
        self.playlists[ctx.guild.id] = playlist
        to_add = (song, title)
        playlist.add_song(to_add)
        await ctx.send(f"`Added {title} to the playlist.`")
        if not ctx.voice_client.is_playing():
            self.bot.dispatch("track_end", ctx)

    @commands.Cog.listener()
    async def on_track_end(self, ctx: commands.Context):
        playlist = self.playlists.get(ctx.guild.id)
        if playlist and not playlist.is_empty:
            song, title = playlist.get_song()
        else:
            await ctx.send("No more songs in the playlist")
            return await ctx.guild.voice_client.disconnect()
        await ctx.send(f"Now playing: {title}")
        
        ctx.guild.voice_client.play(song, after=functools.partial(lambda x: self.bot.loop.create_task(self.check_play(ctx))))
        # for the above code, instead of functools.partial, you could also create_task on the next line, I just find using the `after` kwargs much better

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='Relatively simple music bot example',
    intents=intents,
)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(token())


asyncio.run(main())