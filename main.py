import discord
from discord.ext import commands

from private import token

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import random as rn

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

drawList = ["🍉","💣","💵","⭐️","🚀","💎"]

pokerCard = [
"1♣️A 1",
"1♣️2 2",
"1♣️3 3",
"1♣️4 4",
"1♣️5 5",
"1♣️6 6",
"1♣️7 7",
"1♣️8 8",
"1♣️9 9",
"1♣️10 10",
"1♣️J 11",
"1♣️Q 12",
"1♣️K 13",
"3♠️A 1",
"3♠️2 2",
"3♠️3 3",
"3♠️4 4",
"3♠️5 5",
"3♠️6 6",
"3♠️7 7",
"3♠️8 8",
"3♠️9 9",
"3♠️10 10",
"3♠️J 11",
"3♠️Q 12",
"3♠️K 13",
"0♦️A 1",
"0♦️2 2",
"0♦️3 3",
"0♦️4 4",
"0♦️5 5",
"0♦️6 6",
"0♦️7 7",
"0♦️8 8",
"0♦️9 9",
"0♦️10 10",
"0♦️J 11",
"0♦️Q 12",
"0♦️K 13",
"2♥️A 1",
"2♥️2 2",
"2♥️3 3",
"2♥️4 4",
"2♥️5 5",
"2♥️6 6",
"2♥️7 7",
"2♥️8 8",
"2♥️9 9",
"2♥️10 10",
"2♥️J 11",
"2♥️Q 12",
"2♥️K 13"]

@client.event
async def on_ready():
    print("---------------")
    print("Ready")
    print("---------------")

@client.command()
async def command(ctx):
    await ctx.send("! as prefix\n1. hello\n2. dice\n3. poker5\n4. poker1\n5. slot\n6. time\n7. join\n8. leave\n9. embed")

@client.command()
async def hello(ctx):
    await ctx.send("hi!👋")

@client.command()
async def dice(ctx):
    emoji = "🎲"
    await ctx.send(f"{emoji} {rn.randint(1,6)}")

@client.command()
async def dice3(ctx):
    emoji = "🎲"
    await ctx.send(f"{emoji} {rn.randint(1,6)}, {rn.randint(1,6)}, {rn.randint(1,6)}")

@client.command()
async def draw(ctx):
    emoji = "🎰"
    await ctx.send(f"{emoji} ⭐️ ⭐️ ⭐️\nCongratulations!!!🎉🎊")

@client.command()
async def slot(ctx):
    emoji = "🎰"
    chance = rn.randint(0,9)
    if chance == 7:
        chosen = rn.choice(drawList)
        await ctx.send(f"{emoji}: {chosen} {chosen} {chosen}\nCongratulations!!! 🎉")
    else:
        first, second, third = rn.choice(drawList), rn.choice(drawList), rn.choice(drawList)
        if first == second and second == third:
            await ctx.send(f"{emoji}: {first} {second} {third}\nCongratulations!!! 🎉🎊")
        else:
            await ctx.send(f"{emoji}: {first} {second} {third}\nBetter luck next time!")

@client.command()
async def poker5(ctx):
    emoji = "🃏"
    hashset = set()
    hand = [[],[],[],[]]
    show = f"{emoji}"
    for card in range(5):
        while True:
            cur = rn.choice(pokerCard)
            if cur in hashset:
                continue
            else:
                if cur[0] == "0":
                    hashset.add(cur)
                    hand[0].append(cur[1:])
                elif cur[0] == "1":
                    hashset.add(cur)
                    hand[1].append(cur[1:])
                elif cur[0] == "2":
                    hashset.add(cur)
                    hand[2].append(cur[1:])
                elif cur[0] == "3":
                    hashset.add(cur)
                    hand[3].append(cur[1:])
                else:
                    print("error")
                break
    for card in hand:
        card.sort(key = lambda x:int(x.split()[1]))
        for i in range(len(card)):
            show += card[i].split()[0] + " "
    await ctx.send(show)

@client.command()
async def poker(ctx):
    emoji = "🃏"
    hashset = set()
    hand = [[],[],[],[]]
    show = f"{emoji}"
    for card in range(5):
        while True:
            cur = rn.choice(pokerCard)
            if cur in hashset:
                continue
            else:
                if cur[0] == "0":
                    hashset.add(cur)
                    hand[0].append(cur[1:])
                elif cur[0] == "1":
                    hashset.add(cur)
                    hand[1].append(cur[1:])
                elif cur[0] == "2":
                    hashset.add(cur)
                    hand[2].append(cur[1:])
                elif cur[0] == "3":
                    hashset.add(cur)
                    hand[3].append(cur[1:])
                else:
                    print("error")
                break
    for card in hand:
        card.sort(key = lambda x:int(x.split()[1]))
        for i in range(len(card)):
            show += card[i].split()[0] + " "
    await ctx.send(show)

@client.command()
async def poker1(ctx):
    emoji = "🃏"
    show = rn.choice(pokerCard)[1:].split()[0]
    print(show)
    await ctx.send(f"{emoji}: {show}")

@client.command()
async def time(ctx):
    now_HK = datetime.now(ZoneInfo('Asia/Macau'))
    now_Can = datetime.now(ZoneInfo('Canada/Eastern'))
    now_Eng = datetime.now(ZoneInfo('Europe/Guernsey'))
    now_HK = str(now_HK).split("t")[0].split(".")[0].split()
    now_Can = str(now_Can).split("t")[0].split(".")[0].split()
    now_Eng = str(now_Eng).split("t")[0].split(".")[0].split()
    timeHK = ""
    timeCan = ""
    timeEng = ""
    for i in range(2):
        timeHK += now_HK[i] + " "
        timeCan += now_Can[i] + " "
        timeEng += now_Eng[i] + " "
    emoji = "🕙"
    await ctx.send(f"{emoji}\nHong Kong time: {timeHK}\nCanada time: {timeCan}\nUK time: {timeEng}")

@client.command()
async def embed(ctx, *, msg):
    await ctx.message.delete()
    await ctx.send(msg)

@client.command(pass_context = True)
async def join(ctx):
    if (ctx.author.voice):
        channel = ctx.message.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("我唔理啊！")

@client.command(pass_context = True)
async def leave(ctx):
    if (ctx.voice_client):
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send("我唔理啊！")

@client.listen()
async def on_message(message):
    if message.author == client.user:
        return
    if "gmenu" in message.content.lower():
        emoji = "🥪"
        await message.add_reaction(emoji)
    elif "g." in message.content.lower():
        emoji = "🐔"
        await message.add_reaction(emoji)
    elif "gn" in message.content.lower():
        emoji = "🌛"
        await message.add_reaction(emoji)
    elif "gm" in message.content.lower():
        emoji = "🌞"
        await message.add_reaction(emoji)
    elif "hi" in message.content.lower() or "hello" in message.content.lower():
        emoji = "👋"
        await message.add_reaction(emoji)

import youtube_dl

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
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@client.command()
async def stream(self, ctx, *, url):
    print(url)
    """Streams from a url (same as yt, but doesn't predownload)"""

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'Now playing: {player.title}')

client.run(token())