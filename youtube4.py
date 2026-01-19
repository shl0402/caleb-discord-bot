import discord
from discord.ext import commands
import asyncio
import yt_dlp
from private import token
import tempfile
import shutil
import glob

# Use the certifi Package to ensure up-to-date CA certificates
import os, certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

# Create a temporary directory for downloaded songs
TEMP_DIR = tempfile.mkdtemp(prefix="discord_music_")
print(f"Temporary music directory: {TEMP_DIR}")

# Enable message content intent (required for discord.py 2.x)
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Event handler when bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    # Clean up any stale voice connections
    for voice_client in bot.voice_clients:
        try:
            await voice_client.disconnect(force=True)
        except:
            pass
    print("Voice connections cleaned up")
    # Start periodic cleanup task
    bot.loop.create_task(periodic_cleanup())

# Event handler when bot is closed
@bot.event
async def on_disconnect():
    cleanup_temp_files()

def cleanup_temp_files():
    """Clean up all temporary files"""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            print(f"Cleaned up temporary directory: {TEMP_DIR}")
    except Exception as e:
        print(f"Error cleaning up temp directory: {e}")

def cleanup_empty_files():
    """Clean up empty or partial download files"""
    try:
        pattern = os.path.join(TEMP_DIR, "*")
        for file_path in glob.glob(pattern):
            try:
                if os.path.isfile(file_path):
                    # Remove empty files or very small files (likely corrupted)
                    if os.path.getsize(file_path) < 1024:  # Less than 1KB
                        os.remove(file_path)
                        print(f"Removed empty/corrupt file: {file_path}")
            except Exception as e:
                print(f"Error checking file {file_path}: {e}")
    except Exception as e:
        print(f"Error in cleanup_empty_files: {e}")

# Background task to periodically clean up empty files
async def periodic_cleanup():
    await bot.wait_until_ready()
    while not bot.is_closed():
        cleanup_empty_files()
        await asyncio.sleep(300)  # Run every 5 minutes

# A dictionary to hold per-guild queues.
queues = {}

# A dictionary to hold per-guild loop lists.
loop_lists = {}

# A dictionary to track the current position in the loop list.
loop_positions = {}

# Track if playback was stopped (to resume from stopped position)
stopped_state = {}

# yt_dlp options – using yt_dlp for best audio quality.
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(TEMP_DIR, '%(extractor)s-%(id)s-%(title)s.%(ext)s'),
    'restrictfilenames': True,
    'noplaylist': True,  # Only download single song, not playlists
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cachedir': False,  # Disable cache to prevent empty file issues
    'overwrites': True,  # Overwrite existing files
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
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        except Exception as e:
            # Clean up any partial downloads
            pattern = os.path.join(TEMP_DIR, "*")
            for file in glob.glob(pattern):
                try:
                    if os.path.isfile(file) and os.path.getsize(file) == 0:
                        os.remove(file)
                except:
                    pass
            raise Exception(f"Failed to download: {e}")
        
        if data is None:
            raise Exception("Could not retrieve information from the provided URL.")
        if 'entries' in data:
            data = data['entries'][0]
        # Prepare filename from the downloaded file.
        filename = ytdl.prepare_filename(data)
        
        # Check if file exists and is not empty
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            raise Exception("Downloaded file is empty or doesn't exist")
        
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, filename=filename)

# Function to play the next song in the queue.
async def play_next(ctx, allow_loop=True):
    guild_id = ctx.guild.id
    
    # Check if stopped
    if stopped_state.get(guild_id, False):
        return
    
    # Check if voice client is still connected
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        return
    
    # First check if there are songs in the regular queue
    if queues.get(guild_id):
        next_url = queues[guild_id].pop(0)
        try:
            source = await YTDLSource.create_source(next_url, loop=bot.loop, stream=False)
        except Exception as e:
            print(f"Error processing next song: {e}")
            # Try next song without spamming chat
            await play_next(ctx, allow_loop)
            return

        def after_play(error):
            if error:
                print(f"Playback error: {error}")
            # Clean up the file
            try:
                if os.path.exists(source.filename):
                    # Wait a bit for FFmpeg to release the file
                    import time
                    time.sleep(0.5)
                    os.remove(source.filename)
                    print(f"Cleaned up: {source.filename}")
            except Exception as ex:
                print(f"Error cleaning up file: {ex}")
                # Try again after a delay
                try:
                    time.sleep(1)
                    if os.path.exists(source.filename):
                        os.remove(source.filename)
                except:
                    pass
            bot.loop.create_task(play_next(ctx, allow_loop))

        ctx.voice_client.play(source, after=after_play)
        await ctx.send(f"▶️ Now playing: **{source.title}**")
    # If queue is empty, check if there are songs in the loop list (only if allowed)
    elif allow_loop and loop_lists.get(guild_id):
        loop_list = loop_lists[guild_id]
        if not loop_list:
            print("Loop list is empty")
            return
        
        # Get the current position in the loop list
        if guild_id not in loop_positions:
            loop_positions[guild_id] = 0
        
        position = loop_positions[guild_id]
        next_url = loop_list[position]
        
        # Move to the next position (wrap around to 0 if at the end)
        loop_positions[guild_id] = (position + 1) % len(loop_list)
        
        try:
            source = await YTDLSource.create_source(next_url, loop=bot.loop, stream=False)
        except Exception as e:
            print(f"Error processing loop song: {e}")
            # Try next song in loop without spamming chat
            await play_next(ctx, allow_loop)
            return

        def after_play(error):
            if error:
                print(f"Playback error: {error}")
            # Clean up the file
            try:
                if os.path.exists(source.filename):
                    # Wait a bit for FFmpeg to release the file
                    import time
                    time.sleep(0.5)
                    os.remove(source.filename)
                    print(f"Cleaned up: {source.filename}")
            except Exception as ex:
                print(f"Error cleaning up file: {ex}")
                # Try again after a delay
                try:
                    time.sleep(1)
                    if os.path.exists(source.filename):
                        os.remove(source.filename)
                except:
                    pass
            bot.loop.create_task(play_next(ctx, allow_loop))

        ctx.voice_client.play(source, after=after_play)
        print(f"Now playing (loop): {source.title}")
    else:
        if not allow_loop and loop_lists.get(guild_id):
            print("Queue is empty, loop list available but not allowed")
        else:
            print("Queue and loop list are both empty")

# Command to have the bot join the caller's voice channel.
@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        guild_id = ctx.guild.id
        
        # If already connected to same channel
        if ctx.voice_client is not None:
            if ctx.voice_client.channel.id == channel.id:
                return await ctx.send(f"Already connected to **{channel.name}**")
            await ctx.voice_client.disconnect(force=True)
            await asyncio.sleep(2)
        
        try:
            await channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
            queues[guild_id] = []
            loop_lists[guild_id] = []
            loop_positions[guild_id] = 0
            stopped_state[guild_id] = False
            await ctx.send(f"✅ Joined **{channel.name}**")
        except Exception as e:
            await ctx.send(f"❌ Failed to join: {e}")
    else:
        await ctx.send("You must be in a voice channel to use this command.")

# !play command – plays immediately if nothing is playing, or adds to the queue.
# If no URL is provided, it continues playing from queue or loop list.
@bot.command(name='play')
async def play(ctx, *, url=None):
    # Ensure the bot is connected.
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.invoke(join)
        else:
            return await ctx.send("You are not connected to a voice channel.")
    
    guild_id = ctx.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    
    # If URL is provided, add to queue
    if url is not None:
        queues[guild_id].append(url)
        await ctx.send(f"➕ Added to queue")
        
        # Check if voice client exists (after potential join)
        if ctx.voice_client is None:
            return
        
        # If nothing is playing and not stopped, start playing
        if not ctx.voice_client.is_playing() and not stopped_state.get(guild_id, False):
            await play_next(ctx, allow_loop=True)
        elif stopped_state.get(guild_id, False):
            # Resume from stopped state
            stopped_state[guild_id] = False
            await play_next(ctx, allow_loop=True)
    else:
        # No URL provided - check if there's anything in the queue
        if queues.get(guild_id):
            # Check if voice client exists
            if ctx.voice_client is None:
                return
            
            # Resume from stopped state if stopped
            if stopped_state.get(guild_id, False):
                stopped_state[guild_id] = False
                await play_next(ctx, allow_loop=False)
            elif not ctx.voice_client.is_playing():
                await play_next(ctx, allow_loop=False)
            else:
                await ctx.send("Already playing from queue.")
        else:
            await ctx.send("Queue is empty. Add a song with `!play <url>`")

# Command to skip the current song (or skip a specific link if provided).
@bot.command(name='skip')
async def skip(ctx, *, url=None):
    guild_id = ctx.guild.id
    
    # If URL provided, remove it from queue or loop list
    if url is not None:
        removed = False
        # Try to remove from queue
        if guild_id in queues and url in queues[guild_id]:
            queues[guild_id].remove(url)
            await ctx.send(f"Removed from queue: {url}")
            removed = True
        # Try to remove from loop list
        if guild_id in loop_lists and url in loop_lists[guild_id]:
            loop_lists[guild_id].remove(url)
            # Adjust position if needed
            if loop_lists[guild_id]:
                loop_positions[guild_id] = loop_positions.get(guild_id, 0) % len(loop_lists[guild_id])
            else:
                loop_positions[guild_id] = 0
            await ctx.send(f"Removed from loop list: {url}")
            removed = True
        
        if not removed:
            await ctx.send("That URL is not in the queue or loop list.")
        return
    
    # Skip current song
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped the current song.")
    else:
        await ctx.send("Nothing is playing right now.")

# Command to stop playing (preserves queue/loop - use play/loop to continue).
@bot.command(name='stop')
async def stop(ctx):
    guild_id = ctx.guild.id
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        stopped_state[guild_id] = True
        await ctx.send("⏸️ Stopped playback. Use `!play` or `!loop` to continue.")
    else:
        await ctx.send("Nothing is playing right now.")

# Command to add a song to the loop list (or continue playing if no URL provided).
@bot.command(name='loop')
async def loop_song(ctx, *, url=None):
    # Ensure the bot is connected.
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.invoke(join)
        else:
            return await ctx.send("You are not connected to a voice channel.")
    
    guild_id = ctx.guild.id
    if guild_id not in loop_lists:
        loop_lists[guild_id] = []
    
    # If URL is provided, add to loop list
    if url is not None:
        loop_lists[guild_id].append(url)
        await ctx.send(f"🔁 Added to loop ({len(loop_lists[guild_id])} total)")
    
    # Check again if voice client exists (after potential join)
    if ctx.voice_client is None:
        return
    
    # If nothing is playing and not stopped, start playing from loop
    if not ctx.voice_client.is_playing() and not stopped_state.get(guild_id, False):
        if loop_lists[guild_id]:
            await play_next(ctx, allow_loop=True)
        elif url is None:
            await ctx.send("Loop list is empty. Add a song with `!loop <url>`")
    elif stopped_state.get(guild_id, False):
        # Resume from stopped state
        stopped_state[guild_id] = False
        if loop_lists[guild_id] or queues.get(guild_id):
            await play_next(ctx, allow_loop=True)
        else:
            await ctx.send("Both queue and loop list are empty.")

# Command to remove a song from the loop list.
@bot.command(name='deloop')
async def deloop_song(ctx, *, url):
    guild_id = ctx.guild.id
    if guild_id in loop_lists and url in loop_lists[guild_id]:
        loop_lists[guild_id].remove(url)
        # Reset position if needed
        if loop_lists[guild_id]:
            loop_positions[guild_id] = loop_positions.get(guild_id, 0) % len(loop_lists[guild_id])
        else:
            loop_positions[guild_id] = 0
        await ctx.send(f"➖ Removed from loop ({len(loop_lists[guild_id])} remaining)")
    else:
        await ctx.send("That URL is not in the loop list.")

# Command to view the loop list.
@bot.command(name='looplist')
async def view_loop_list(ctx):
    guild_id = ctx.guild.id
    if guild_id in loop_lists and loop_lists[guild_id]:
        message = "🔁 **Loop List:**\n" + "\n".join([f"{i+1}. {song}" for i, song in enumerate(loop_lists[guild_id])])
        await ctx.send(message)
    else:
        await ctx.send("The loop list is empty.")

# Command to view the current queue.
@bot.command(name='queue')
async def view_queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        message = "📋 **Queue:**\n" + "\n".join([f"{i+1}. {song}" for i, song in enumerate(queues[guild_id])])
        await ctx.send(message)
    else:
        await ctx.send("The queue is empty.")

# Command to display help information.
@bot.command(name='help')
async def help_command(ctx):
    help_message = """
**🎵 Music Bot Commands**

**Connection:**
`!join` - Join your voice channel
`!leave` - Leave voice channel

**Playback:**
`!play <url>` - Add song to queue and play
`!play` - Continue playing from queue/loop
`!loop <url>` - Add song to loop list and play
`!loop` - Continue playing from loop
`!stop` - Stop current song (preserves queue/loop)
`!skip` - Skip to next song
`!skip <url>` - Remove specific URL from queue/loop

**Queue & Loop:**
`!queue` - View current queue
`!looplist` - View loop list
`!deloop <url>` - Remove song from loop list

**How it works:**
• **Queue songs** play first (in order)
• When queue is empty, **loop songs** play continuously
• Use `!stop` to pause, then `!play` or `!loop` to resume
• Loop songs repeat automatically in order
"""
    await ctx.send(help_message)

# Command to leave the voice channel.
@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        guild_id = ctx.guild.id
        # Stop playback
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await asyncio.sleep(0.5)
        await ctx.voice_client.disconnect(force=True)
        # Clear all data
        queues.pop(guild_id, None)
        loop_lists.pop(guild_id, None)
        loop_positions.pop(guild_id, None)
        stopped_state.pop(guild_id, None)
        await ctx.send("👋 Disconnected from the voice channel.")
    else:
        await ctx.send("I'm not connected to any voice channel.")

if __name__ == "__main__":
    try:
        bot.run(token())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        cleanup_temp_files()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        cleanup_temp_files()
