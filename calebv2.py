"""
Caleb Bot v2 - Combined Discord Bot
Features:
1. Role Assignment via Emoji Reactions (from caleb.py)
2. Drink Counter with per-channel tracking (from drinkv2.py)
3. YouTube Music Player with queue (from youtube5.py)

All features include both prefix commands (!) and slash commands (/)
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiosqlite
import yt_dlp
from pathlib import Path
from datetime import datetime
from typing import Optional
import os
import time

# Use certifi for SSL certificates
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
except ImportError:
    pass

# Check for voice support
try:
    import nacl
except ImportError:
    print("WARNING: PyNaCl is not installed. Voice support will not work!")
    print("Please install it with: pip install PyNaCl")

# Load Discord token from environment variable
# Set it in terminal: export DISCORD_TOKEN="your_token_here" (Linux/Mac)
# Or in Windows: set DISCORD_TOKEN=your_token_here
# Or in PowerShell: $env:DISCORD_TOKEN="your_token_here"
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not set!")
    print("Set it with: export DISCORD_TOKEN='your_token_here'")
    exit(1)

# ========================= CONFIGURATION =========================

# Database file path for drink counter
DB_PATH = Path(__file__).parent / "drink_counter.db"

# Role Assignment: Map emoji to role name
EMOJI_ROLE_MAP = {
    "🕹️": "gamers",
    "🫂": "caleb",
    "💃": "犯人",
    "🤫": "共犯",
    "🐕": "神犬",
}

# Tracked message IDs for role assignment
ROLE_MESSAGE_IDS = {
    1261173511511216231: 0,
    1261157962702127104: 0,
}

# ========================= YOUTUBE CONFIG =========================

# Path to cookies file (same folder as this script)
COOKIES_FILE = Path(__file__).parent / "cookies.txt"

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# Add cookies only if file exists
if COOKIES_FILE.exists():
    ytdl_format_options['cookiefile'] = str(COOKIES_FILE)
    print(f"[YouTube] Using cookies from: {COOKIES_FILE}")

ffmpeg_options = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel quiet'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


# ========================= YOUTUBE SOURCE =========================

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, filename, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.filename = filename

    @classmethod
    async def create_source(cls, url, *, loop, stream=False):
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        if data is None:
            raise Exception("Could not retrieve information from the provided URL.")
        if 'entries' in data:
            data = data['entries'][0]
        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, filename=filename)


# ========================= ROLE ASSIGNMENT COG =========================

class RoleAssignment(commands.Cog):
    """Cog for handling role assignment via emoji reactions"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.role_messages = ROLE_MESSAGE_IDS.copy()
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[RoleAssignment] Cog loaded!")
    
    @commands.command(name="setuproles")
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx: commands.Context):
        """Send the role assignment message with all reaction emojis."""
        embed = discord.Embed(
            title="🎭 Role Assignment",
            description="React to this message to get your role!",
            color=discord.Color.blue()
        )
        
        role_list = "\n".join([f"{emoji} : {role}" for emoji, role in EMOJI_ROLE_MAP.items()])
        embed.add_field(name="Available Roles", value=role_list, inline=False)
        embed.set_footer(text="Click on an emoji to get/remove the corresponding role")
        
        message = await ctx.send(embed=embed)
        for emoji in EMOJI_ROLE_MAP.keys():
            await message.add_reaction(emoji)
        
        self.role_messages[message.id] = ctx.channel.id
        print(f"[RoleAssignment] Setup message created: {message.id}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        
        emoji_str = str(payload.emoji)
        if emoji_str not in EMOJI_ROLE_MAP:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return
        
        role_name = EMOJI_ROLE_MAP[emoji_str]
        role = discord.utils.get(guild.roles, name=role_name)
        
        if role is None:
            print(f"[RoleAssignment] Role '{role_name}' not found")
            return
        
        try:
            await member.add_roles(role, reason="Role assignment via reaction")
            print(f"[RoleAssignment] Added '{role_name}' to {member.display_name}")
        except discord.Forbidden:
            print(f"[RoleAssignment] Permission denied for '{role_name}'")
        except discord.HTTPException as e:
            print(f"[RoleAssignment] Error: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        emoji_str = str(payload.emoji)
        if emoji_str not in EMOJI_ROLE_MAP:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return
        
        role_name = EMOJI_ROLE_MAP[emoji_str]
        role = discord.utils.get(guild.roles, name=role_name)
        
        if role is None:
            return
        
        try:
            await member.remove_roles(role, reason="Role removal via reaction")
            print(f"[RoleAssignment] Removed '{role_name}' from {member.display_name}")
        except (discord.Forbidden, discord.HTTPException):
            pass


# ========================= DRINK COUNTER COG =========================

class DrinkCounter(commands.Cog):
    """Cog for tracking drink debts between users (per-channel)"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
    
    async def cog_load(self):
        await self.init_db()
        print(f"[DrinkCounter] Cog loaded! Database: {self.db_path}")
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS drink_debts_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    debtor_id INTEGER NOT NULL,
                    creditor_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL DEFAULT 1,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, channel_id, debtor_id, creditor_id)
                )
            """)
            await db.commit()
    
    async def add_drink_debt(self, guild_id: int, channel_id: int, debtor_id: int, 
                             creditor_id: int, amount: int = 1, reason: str = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT amount FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND debtor_id = ? AND creditor_id = ?",
                (guild_id, channel_id, debtor_id, creditor_id)
            )
            row = await cursor.fetchone()
            
            if row:
                new_amount = row[0] + amount
                await db.execute(
                    "UPDATE drink_debts_v2 SET amount = ? WHERE guild_id = ? AND channel_id = ? AND debtor_id = ? AND creditor_id = ?",
                    (new_amount, guild_id, channel_id, debtor_id, creditor_id)
                )
            else:
                new_amount = amount
                await db.execute(
                    "INSERT INTO drink_debts_v2 (guild_id, channel_id, debtor_id, creditor_id, amount, reason) VALUES (?, ?, ?, ?, ?, ?)",
                    (guild_id, channel_id, debtor_id, creditor_id, amount, reason)
                )
            
            await db.commit()
            return new_amount
    
    async def pay_drink_debt(self, guild_id: int, channel_id: int, debtor_id: int, 
                             creditor_id: int, amount: int = 1) -> tuple[bool, int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT amount FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND debtor_id = ? AND creditor_id = ?",
                (guild_id, channel_id, debtor_id, creditor_id)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] <= 0:
                return False, 0
            
            new_amount = max(0, row[0] - amount)
            
            if new_amount == 0:
                await db.execute(
                    "DELETE FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND debtor_id = ? AND creditor_id = ?",
                    (guild_id, channel_id, debtor_id, creditor_id)
                )
            else:
                await db.execute(
                    "UPDATE drink_debts_v2 SET amount = ? WHERE guild_id = ? AND channel_id = ? AND debtor_id = ? AND creditor_id = ?",
                    (new_amount, guild_id, channel_id, debtor_id, creditor_id)
                )
            
            await db.commit()
            return True, new_amount
    
    async def get_user_debts(self, guild_id: int, channel_id: int, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute(
                "SELECT creditor_id, amount FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND debtor_id = ? AND amount > 0",
                (guild_id, channel_id, user_id)
            )
            owes = await cursor.fetchall()
            
            cursor = await db.execute(
                "SELECT debtor_id, amount FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND creditor_id = ? AND amount > 0",
                (guild_id, channel_id, user_id)
            )
            owed = await cursor.fetchall()
            
            return {
                "owes": [(row["creditor_id"], row["amount"]) for row in owes],
                "owed": [(row["debtor_id"], row["amount"]) for row in owed]
            }
    
    async def get_all_debts(self, guild_id: int, channel_id: int) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT debtor_id, creditor_id, amount FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND amount > 0 ORDER BY amount DESC",
                (guild_id, channel_id)
            )
            return await cursor.fetchall()

    # ===== PREFIX COMMANDS =====
    
    @commands.command(name="owe")
    async def cmd_owe(self, ctx: commands.Context, debtor: discord.Member, 
                      creditor: discord.Member, amount: int = 1, *, reason: str = None):
        if debtor == creditor:
            return await ctx.send("❌ A person can't owe themselves a drink!")
        if amount <= 0 or amount > 100:
            return await ctx.send("❌ Amount must be between 1 and 100!")
        
        new_total = await self.add_drink_debt(ctx.guild.id, ctx.channel.id, debtor.id, creditor.id, amount, reason)
        
        embed = discord.Embed(
            title=f"{'🍺' if amount == 1 else '🍻'} Drink Debt Added!",
            description=f"**{debtor.display_name}** now owes **{creditor.display_name}** {new_total} drink(s)!" + 
                       (f"\n📝 Reason: {reason}" if reason else ""),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"#{ctx.channel.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="paid")
    async def cmd_paid(self, ctx: commands.Context, debtor: discord.Member, 
                       creditor: discord.Member, amount: int = 1):
        success, remaining = await self.pay_drink_debt(ctx.guild.id, ctx.channel.id, debtor.id, creditor.id, amount)
        
        if not success:
            return await ctx.send(f"❌ {debtor.display_name} doesn't owe {creditor.display_name} any drinks here!")
        
        if remaining == 0:
            embed = discord.Embed(
                title="✅ Debt Cleared!",
                description=f"**{debtor.display_name}** paid off their debt to **{creditor.display_name}**! 🎉",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title="🍺 Drink Paid!",
                description=f"**{debtor.display_name}** paid {amount} drink(s). Remaining: {remaining}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
        embed.set_footer(text=f"#{ctx.channel.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="drinks")
    async def cmd_drinks(self, ctx: commands.Context, user: discord.Member = None):
        target = user or ctx.author
        debts = await self.get_user_debts(ctx.guild.id, ctx.channel.id, target.id)
        
        embed = discord.Embed(title=f"🍻 Drink Status: {target.display_name}", color=discord.Color.gold())
        
        if debts["owes"]:
            owes_text = "\n".join([f"• {ctx.guild.get_member(cid).display_name if ctx.guild.get_member(cid) else 'Unknown'}: {amt} 🍺" 
                                   for cid, amt in debts["owes"]])
            embed.add_field(name=f"📤 Owes ({sum(a for _, a in debts['owes'])} total)", value=owes_text, inline=False)
        else:
            embed.add_field(name="📤 Owes", value="Nobody! 🎉", inline=False)
        
        if debts["owed"]:
            owed_text = "\n".join([f"• {ctx.guild.get_member(did).display_name if ctx.guild.get_member(did) else 'Unknown'}: {amt} 🍺" 
                                   for did, amt in debts["owed"]])
            embed.add_field(name=f"📥 Is Owed ({sum(a for _, a in debts['owed'])} total)", value=owed_text, inline=False)
        else:
            embed.add_field(name="📥 Is Owed", value="Nobody owes them", inline=False)
        
        embed.set_footer(text=f"#{ctx.channel.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard")
    async def cmd_leaderboard(self, ctx: commands.Context):
        debts = await self.get_all_debts(ctx.guild.id, ctx.channel.id)
        
        if not debts:
            embed = discord.Embed(title="🍻 Drink Leaderboard", description="No debts! 🎉", color=discord.Color.green())
        else:
            embed = discord.Embed(title="🍻 Drink Leaderboard", color=discord.Color.gold())
            debt_text = "\n".join([
                f"{i}. **{ctx.guild.get_member(d['debtor_id']).display_name if ctx.guild.get_member(d['debtor_id']) else 'Unknown'}** → "
                f"**{ctx.guild.get_member(d['creditor_id']).display_name if ctx.guild.get_member(d['creditor_id']) else 'Unknown'}**: {d['amount']} 🍺"
                for i, d in enumerate(debts[:15], 1)
            ])
            embed.add_field(name="Debts", value=debt_text, inline=False)
        
        embed.set_footer(text=f"#{ctx.channel.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="drinkhelp")
    async def cmd_drinkhelp(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🍻 Drink Counter Help",
            description="Track who owes drinks!\n**Each channel has its own leaderboard!**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Commands", value="""
`/owe @debtor @creditor [amount] [reason]` - Record a debt
`/paid @debtor @creditor [amount]` - Record payment
`/drinks [@user]` - Check status
`/leaderboard` - Show all debts
        """, inline=False)
        await ctx.send(embed=embed)

    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="owe", description="Record that someone owes a drink")
    @app_commands.describe(debtor="Who owes", creditor="Who is owed", amount="Number of drinks", reason="Reason")
    async def slash_owe(self, interaction: discord.Interaction, debtor: discord.Member, 
                        creditor: discord.Member, amount: int = 1, reason: str = None):
        if debtor == creditor:
            return await interaction.response.send_message("❌ Can't owe yourself!", ephemeral=True)
        if amount <= 0 or amount > 100:
            return await interaction.response.send_message("❌ Amount: 1-100!", ephemeral=True)
        
        new_total = await self.add_drink_debt(interaction.guild.id, interaction.channel.id, debtor.id, creditor.id, amount, reason)
        
        embed = discord.Embed(
            title=f"{'🍺' if amount == 1 else '🍻'} Drink Debt Added!",
            description=f"**{debtor.display_name}** now owes **{creditor.display_name}** {new_total} drink(s)!" +
                       (f"\n📝 Reason: {reason}" if reason else ""),
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"#{interaction.channel.name}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="paid", description="Record a drink payment")
    @app_commands.describe(debtor="Who paid", creditor="Who was paid", amount="Number of drinks")
    async def slash_paid(self, interaction: discord.Interaction, debtor: discord.Member, 
                         creditor: discord.Member, amount: int = 1):
        success, remaining = await self.pay_drink_debt(interaction.guild.id, interaction.channel.id, debtor.id, creditor.id, amount)
        
        if not success:
            return await interaction.response.send_message(f"❌ No debt found!", ephemeral=True)
        
        embed = discord.Embed(
            title="✅ Debt Cleared!" if remaining == 0 else "🍺 Drink Paid!",
            description=f"**{debtor.display_name}** paid **{creditor.display_name}**" + 
                       (f" 🎉" if remaining == 0 else f". Remaining: {remaining}"),
            color=discord.Color.green() if remaining == 0 else discord.Color.blue()
        )
        embed.set_footer(text=f"#{interaction.channel.name}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="drinks", description="Check drink status")
    @app_commands.describe(user="User to check (default: yourself)")
    async def slash_drinks(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        debts = await self.get_user_debts(interaction.guild.id, interaction.channel.id, target.id)
        
        embed = discord.Embed(title=f"🍻 {target.display_name}", color=discord.Color.gold())
        
        if debts["owes"]:
            owes_text = "\n".join([f"• {interaction.guild.get_member(cid).display_name if interaction.guild.get_member(cid) else '?'}: {amt} 🍺" 
                                   for cid, amt in debts["owes"]])
            embed.add_field(name=f"📤 Owes ({sum(a for _, a in debts['owes'])})", value=owes_text, inline=False)
        else:
            embed.add_field(name="📤 Owes", value="Nobody! 🎉", inline=False)
        
        if debts["owed"]:
            owed_text = "\n".join([f"• {interaction.guild.get_member(did).display_name if interaction.guild.get_member(did) else '?'}: {amt} 🍺" 
                                   for did, amt in debts["owed"]])
            embed.add_field(name=f"📥 Owed ({sum(a for _, a in debts['owed'])})", value=owed_text, inline=False)
        else:
            embed.add_field(name="📥 Owed", value="None", inline=False)
        
        embed.set_footer(text=f"#{interaction.channel.name}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="Show all drink debts in this channel")
    async def slash_leaderboard(self, interaction: discord.Interaction):
        debts = await self.get_all_debts(interaction.guild.id, interaction.channel.id)
        
        if not debts:
            embed = discord.Embed(title="🍻 Leaderboard", description="No debts! 🎉", color=discord.Color.green())
        else:
            embed = discord.Embed(title="🍻 Leaderboard", color=discord.Color.gold())
            debt_text = "\n".join([
                f"{i}. **{interaction.guild.get_member(d['debtor_id']).display_name if interaction.guild.get_member(d['debtor_id']) else '?'}** → "
                f"**{interaction.guild.get_member(d['creditor_id']).display_name if interaction.guild.get_member(d['creditor_id']) else '?'}**: {d['amount']} 🍺"
                for i, d in enumerate(debts[:15], 1)
            ])
            embed.add_field(name="Debts", value=debt_text, inline=False)
        
        embed.set_footer(text=f"#{interaction.channel.name}")
        await interaction.response.send_message(embed=embed)


# ========================= MUSIC COG =========================

class Music(commands.Cog):
    """Cog for YouTube music playback"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}
        self.last_connection_attempt = {}
    
    async def play_next(self, ctx_or_interaction):
        """Play the next song in queue"""
        # Handle both Context and Interaction
        if isinstance(ctx_or_interaction, discord.Interaction):
            guild = ctx_or_interaction.guild
            voice_client = ctx_or_interaction.guild.voice_client
            send = ctx_or_interaction.followup.send
        else:
            guild = ctx_or_interaction.guild
            voice_client = ctx_or_interaction.voice_client
            send = ctx_or_interaction.send
        
        guild_id = guild.id
        if self.queues.get(guild_id):
            next_url = self.queues[guild_id].pop(0)
            try:
                source = await YTDLSource.create_source(next_url, loop=self.bot.loop, stream=False)
            except Exception as e:
                await send(f"Error: {e}")
                return

            def after_play(error):
                try:
                    os.remove(source.filename)
                except:
                    pass
                self.bot.loop.create_task(self.play_next(ctx_or_interaction))

            voice_client.play(source, after=after_play)
            await send(f"🎵 Now playing: **{source.title}**")
        else:
            await send("Queue is empty.")

    # ===== PREFIX COMMANDS =====
    
    @commands.command(name='join')
    async def join(self, ctx):
        """Join voice channel"""
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel!")
        
        channel = ctx.author.voice.channel
        guild_id = ctx.guild.id
        
        now = time.time()
        if guild_id in self.last_connection_attempt:
            if now - self.last_connection_attempt[guild_id] < 3:
                return await ctx.send("Please wait before reconnecting.")
        
        if ctx.voice_client is not None:
            if ctx.voice_client.channel.id == channel.id:
                return await ctx.send(f"Already in **{channel.name}**")
            await ctx.voice_client.disconnect(force=True)
            await asyncio.sleep(2)
        
        self.last_connection_attempt[guild_id] = now
        
        try:
            await channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
            self.queues[guild_id] = []
            await ctx.send(f"✅ Joined **{channel.name}**")
        except Exception as e:
            await ctx.send(f"❌ Failed to join: {e}")
    
    @commands.command(name='play')
    async def play(self, ctx, *, url):
        """Play a song from YouTube"""
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.invoke(self.join)
            else:
                return await ctx.send("You're not in a voice channel!")
        
        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        
        if ctx.voice_client.is_playing():
            self.queues[guild_id].append(url)
            return await ctx.send(f"📝 Added to queue: {url}")
        
        try:
            await ctx.send("🔄 Loading...")
            source = await YTDLSource.create_source(url, loop=self.bot.loop, stream=False)
        except Exception as e:
            return await ctx.send(f"Error: {e}")

        def after_play(error):
            try:
                os.remove(source.filename)
            except:
                pass
            self.bot.loop.create_task(self.play_next(ctx))

        ctx.voice_client.play(source, after=after_play)
        await ctx.send(f"🎵 Now playing: **{source.title}**")
    
    @commands.command(name='skip')
    async def skip(self, ctx):
        """Skip current song"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭️ Skipped!")
        else:
            await ctx.send("Nothing playing.")
    
    @commands.command(name='queue')
    async def view_queue(self, ctx):
        """View the queue"""
        guild_id = ctx.guild.id
        if guild_id in self.queues and self.queues[guild_id]:
            msg = "📜 Queue:\n" + "\n".join([f"{i+1}. {song}" for i, song in enumerate(self.queues[guild_id][:10])])
            await ctx.send(msg)
        else:
            await ctx.send("Queue is empty.")
    
    @commands.command(name='leave')
    async def leave(self, ctx):
        """Leave voice channel"""
        if ctx.voice_client:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await ctx.voice_client.disconnect(force=True)
            self.queues.pop(ctx.guild.id, None)
            await ctx.send("👋 Disconnected!")
        else:
            await ctx.send("Not in a voice channel.")
    
    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pause playback"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Paused!")
        else:
            await ctx.send("Nothing playing.")
    
    @commands.command(name='resume')
    async def resume(self, ctx):
        """Resume playback"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Resumed!")
        else:
            await ctx.send("Nothing paused.")

    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="join", description="Join your voice channel")
    async def slash_join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("You must be in a voice channel!", ephemeral=True)
        
        channel = interaction.user.voice.channel
        guild_id = interaction.guild.id
        
        now = time.time()
        if guild_id in self.last_connection_attempt:
            if now - self.last_connection_attempt[guild_id] < 3:
                return await interaction.response.send_message("Please wait before reconnecting.", ephemeral=True)
        
        await interaction.response.defer()
        
        if interaction.guild.voice_client is not None:
            if interaction.guild.voice_client.channel.id == channel.id:
                return await interaction.followup.send(f"Already in **{channel.name}**")
            await interaction.guild.voice_client.disconnect(force=True)
            await asyncio.sleep(2)
        
        self.last_connection_attempt[guild_id] = now
        
        try:
            await channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
            self.queues[guild_id] = []
            await interaction.followup.send(f"✅ Joined **{channel.name}**")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {e}")
    
    @app_commands.command(name="play", description="Play a song from YouTube")
    @app_commands.describe(query="YouTube URL or search query")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        if interaction.guild.voice_client is None:
            if interaction.user.voice:
                await interaction.response.defer()
                channel = interaction.user.voice.channel
                try:
                    await channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
                    self.queues[interaction.guild.id] = []
                except Exception as e:
                    return await interaction.followup.send(f"❌ Failed to join: {e}")
            else:
                return await interaction.response.send_message("You're not in a voice channel!", ephemeral=True)
        else:
            await interaction.response.defer()
        
        guild_id = interaction.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        
        if interaction.guild.voice_client.is_playing():
            self.queues[guild_id].append(query)
            return await interaction.followup.send(f"📝 Added to queue: {query}")
        
        try:
            source = await YTDLSource.create_source(query, loop=self.bot.loop, stream=False)
        except Exception as e:
            return await interaction.followup.send(f"Error: {e}")

        def after_play(error):
            try:
                os.remove(source.filename)
            except:
                pass
            self.bot.loop.create_task(self.play_next(interaction))

        interaction.guild.voice_client.play(source, after=after_play)
        await interaction.followup.send(f"🎵 Now playing: **{source.title}**")
    
    @app_commands.command(name="skip", description="Skip the current song")
    async def slash_skip(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped!")
        else:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
    
    @app_commands.command(name="queue", description="View the music queue")
    async def slash_queue(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        if guild_id in self.queues and self.queues[guild_id]:
            msg = "📜 Queue:\n" + "\n".join([f"{i+1}. {song}" for i, song in enumerate(self.queues[guild_id][:10])])
            await interaction.response.send_message(msg)
        else:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
    
    @app_commands.command(name="leave", description="Leave the voice channel")
    async def slash_leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.is_playing():
                interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect(force=True)
            self.queues.pop(interaction.guild.id, None)
            await interaction.response.send_message("👋 Disconnected!")
        else:
            await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
    
    @app_commands.command(name="pause", description="Pause the music")
    async def slash_pause(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ Paused!")
        else:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
    
    @app_commands.command(name="resume", description="Resume the music")
    async def slash_resume(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ Resumed!")
        else:
            await interaction.response.send_message("Nothing paused.", ephemeral=True)
    
    @app_commands.command(name="musichelp", description="Show music commands")
    async def slash_musichelp(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎵 Music Commands", color=discord.Color.purple())
        embed.add_field(name="Commands", value="""
`/join` - Join voice channel
`/play <url/search>` - Play a song
`/skip` - Skip current song
`/pause` - Pause playback
`/resume` - Resume playback
`/queue` - View queue
`/leave` - Leave channel
        """, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ========================= BOT SETUP =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print("=" * 50)
    print(f"Caleb Bot v2 is ready!")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"Discord.py version: {discord.__version__}")
    print(f"Guilds: {len(bot.guilds)}")
    print("=" * 50)
    
    # Load cogs first (they register slash commands)
    await bot.add_cog(RoleAssignment(bot))
    await bot.add_cog(DrinkCounter(bot))
    await bot.add_cog(Music(bot))
    
    # Now sync - this will replace any old cached commands with only what's currently registered
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands (old commands cleared)")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")
    
    # Set status
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="/help | !help"
    ))
    
    # Clean up voice connections
    for vc in bot.voice_clients:
        try:
            await vc.disconnect(force=True)
        except:
            pass


@bot.event
async def on_voice_state_update(member, before, after):
    """Auto-disconnect when alone in voice channel"""
    if member.id == bot.user.id:
        return
    
    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
    if voice_client and voice_client.channel:
        members = [m for m in voice_client.channel.members if not m.bot]
        if len(members) == 0:
            await voice_client.disconnect()


@bot.command(name="help")
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🤖 Caleb Bot v2 - Help",
        description="All available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🎭 Role Assignment", value="""
`!setuproles` - Create role message (Admin)
React to role messages to get roles!
    """, inline=False)
    
    embed.add_field(name="🍻 Drink Counter", value="""
`/owe @debtor @creditor [amount] [reason]`
`/paid @debtor @creditor [amount]`
`/drinks [@user]` | `/leaderboard`
    """, inline=False)
    
    embed.add_field(name="🎵 Music", value="""
`/join` `/leave` `/play <url>`
`/skip` `/pause` `/resume` `/queue`
    """, inline=False)
    
    embed.set_footer(text="Use / for slash commands or ! for prefix commands")
    await ctx.send(embed=embed)


@bot.tree.command(name="help", description="Show all available commands")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Caleb Bot v2 - Help",
        description="All available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🎭 Role Assignment", value="React to role messages to get roles!", inline=False)
    
    embed.add_field(name="🍻 Drink Counter", value="""
`/owe` `/paid` `/drinks` `/leaderboard`
    """, inline=False)
    
    embed.add_field(name="🎵 Music", value="""
`/join` `/leave` `/play` `/skip` `/pause` `/resume` `/queue`
    """, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("ERROR: Invalid token! Check your DISCORD_TOKEN environment variable.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
