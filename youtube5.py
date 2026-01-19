import discord
from discord.ext import commands
import asyncio
import yt_dlp
from private import token

# Use the certifi Package to ensure up-to-date CA certificates
import os, certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

# Check for voice support
try:
    import nacl
except ImportError:
    print("WARNING: PyNaCl is not installed. Voice support will not work!")
    print("Please install it with: pip install PyNaCl")
    exit(1)

# Enable message content intent (required for discord.py 2.x)
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Required for voice channel events

bot = commands.Bot(command_prefix='!', intents=intents)

# A dictionary to hold per-guild queues.
queues = {}

# Track connection attempts to prevent rapid reconnections
last_connection_attempt = {}

# yt_dlp options – using yt_dlp for best audio quality.
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,  # Only download single song, not playlists
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# FFmpeg options – include reconnect parameters and quiet logging.
ffmpeg_options = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel quiet'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# Class to handle audio source extraction.
# We force a full download (stream=False) so that a local file is saved.
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, filename, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.filename = filename

    @classmethod
    async def create_source(cls, url, *, loop, stream=False):
        # Force download by setting stream=False
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        if data is None:
            raise Exception("Could not retrieve information from the provided URL.")
        if 'entries' in data:
            data = data['entries'][0]
        # Prepare filename from the downloaded file.
        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, filename=filename)

# Function to play the next song in the queue.
async def play_next(ctx):
    guild_id = ctx.guild.id
    if queues.get(guild_id):
        next_url = queues[guild_id].pop(0)
        try:
            source = await YTDLSource.create_source(next_url, loop=bot.loop, stream=False)
        except Exception as e:
            await ctx.send(f"Error processing next song: {e}")
            return

        def after_play(error):
            try:
                os.remove(source.filename)
            except Exception as ex:
                print(f"Error cleaning up file: {ex}")
            bot.loop.create_task(play_next(ctx))

        ctx.voice_client.play(source, after=after_play)
        await ctx.send(f"Now playing: **{source.title}**")
    else:
        await ctx.send("Queue is empty.")

# Command to have the bot join the caller's voice channel.
@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        guild_id = ctx.guild.id
        
        # Check if we recently tried to connect (prevents rate limiting)
        import time
        now = time.time()
        if guild_id in last_connection_attempt:
            if now - last_connection_attempt[guild_id] < 3:
                return await ctx.send("Please wait a moment before trying to connect again.")
        
        # Disconnect if already connected
        if ctx.voice_client is not None:
            if ctx.voice_client.channel.id == channel.id:
                return await ctx.send(f"Already connected to **{channel.name}**")
            await ctx.send("Disconnecting from current channel...")
            await ctx.voice_client.disconnect(force=True)
            await asyncio.sleep(2)  # Important: wait for proper cleanup
        
        last_connection_attempt[guild_id] = now
        
        try:
            await ctx.send("Connecting to voice channel...")
            vc = await channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
            queues[ctx.guild.id] = []
            await ctx.send(f"✅ Successfully joined **{channel.name}**")
        except asyncio.TimeoutError:
            await ctx.send("❌ Connection timeout. Please check your network and try again.")
        except discord.errors.ConnectionClosed as e:
            error_msg = f"❌ Voice connection failed with error {e.code}.\n"
            if e.code == 4006:
                error_msg += "This usually means there's a session conflict. Please:\n"
                error_msg += "1. Make sure no other instances of the bot are running\n"
                error_msg += "2. Wait 10-15 seconds and try again\n"
                error_msg += "3. If the issue persists, use `!cleanup` and restart the bot"
            await ctx.send(error_msg)
        except Exception as e:
            await ctx.send(f"❌ Failed to join voice channel: {e}")
    else:
        await ctx.send("You must be in a voice channel to use this command.")

# !play command – plays immediately if nothing is playing, or adds to the queue.
@bot.command(name='play')
async def play(ctx, *, url):
    # Ensure the bot is connected.
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.invoke(join)
        else:
            return await ctx.send("You are not connected to a voice channel.")
    guild_id = ctx.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    # If a song is already playing, add to the queue.
    if ctx.voice_client.is_playing():
        queues[guild_id].append(url)
        await ctx.send(f"Added to queue: {url}")
    else:
        try:
            source = await YTDLSource.create_source(url, loop=bot.loop, stream=False)
        except Exception as e:
            return await ctx.send(f"Error processing this URL: {e}")

        def after_play(error):
            try:
                os.remove(source.filename)
            except Exception as ex:
                print(f"Error cleaning up file: {ex}")
            bot.loop.create_task(play_next(ctx))

        ctx.voice_client.play(source, after=after_play)
        await ctx.send(f"Now playing: **{source.title}**")

# Command to skip the current song.
@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped the current song.")
    else:
        await ctx.send("Nothing is playing right now.")

# Command to view the current queue.
@bot.command(name='queue')
async def view_queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        message = "Queue:\n" + "\n".join([f"{i+1}. {song}" for i, song in enumerate(queues[guild_id])])
        await ctx.send(message)
    else:
        await ctx.send("The queue is empty.")

# Command to leave the voice channel.
@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        # Stop playing and clean up
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await asyncio.sleep(0.5)
        await ctx.voice_client.disconnect(force=True)
        queues.pop(ctx.guild.id, None)
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("I'm not connected to any voice channel.")

# Add a reconnect command in case of voice issues
@bot.command(name='reconnect')
async def reconnect(ctx):
    """Reconnect to fix voice issues"""
    if ctx.voice_client:
        channel = ctx.voice_client.channel
        await ctx.voice_client.disconnect(force=True)
        await asyncio.sleep(2)  # Wait for cleanup
        try:
            await channel.connect(timeout=30.0, reconnect=True)
            await ctx.send(f"Reconnected to **{channel.name}**")
        except Exception as e:
            await ctx.send(f"Failed to reconnect: {e}")
    else:
        await ctx.send("I'm not connected to any voice channel. Use !join first.")

@bot.command(name='cleanup')
@commands.has_permissions(administrator=True)
async def cleanup(ctx):
    """Force disconnect from all voice channels (Admin only)"""
    disconnected = 0
    for vc in bot.voice_clients:
        try:
            await vc.disconnect(force=True)
            disconnected += 1
        except:
            pass
    queues.clear()
    last_connection_attempt.clear()
    await asyncio.sleep(2)
    await ctx.send(f"✅ Cleaned up {disconnected} voice connection(s). You can now try !join again.")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    # Clean up any existing voice connections on startup
    for vc in bot.voice_clients:
        try:
            await vc.disconnect(force=True)
        except:
            pass
    print("Voice connections cleaned up")

@bot.event
async def on_voice_state_update(member, before, after):
    # Disconnect bot if it's alone in the voice channel
    if member.id == bot.user.id:
        return
    
    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
    if voice_client and voice_client.channel:
        # Count members excluding bots
        members = [m for m in voice_client.channel.members if not m.bot]
        if len(members) == 0:
            await voice_client.disconnect()
            queues.pop(member.guild.id, None)

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'An error occurred: {event}')
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    try:
        bot.run(token())
    except discord.errors.LoginFailure:
        print("ERROR: Invalid token. Please check your token in private.py")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

