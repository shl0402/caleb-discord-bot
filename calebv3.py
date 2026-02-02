"""
Caleb Bot v3 - Combined Discord Bot with Lavalink
Features:
1. Role Assignment via Emoji Reactions
2. Drink Counter with per-channel tracking
3. YouTube Music Player using Lavalink/Wavelink (stable, no YouTube blocking!)

All features include both prefix commands (!) and slash commands (/)
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiosqlite
import wavelink
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

# Load Discord token from environment variable
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
    "🕹": "gamer",
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

# ========================= LAVALINK CONFIG =========================
# Public Lavalink nodes - these handle YouTube downloading so your server doesn't get blocked!
# List from: https://lavalink-list.darrennathanael.com/
# Updated: February 2026 - Public nodes can go offline, check the list for updates!

LAVALINK_NODES = [
    {
        "uri": "http://lava-v3.ajieblogs.eu.org:80",
        "password": "https://dsc.gg/ajidevserver",
    },
    {
        "uri": "http://lavalink.lexnet.cc:2333",
        "password": "lexn3tl@telegramalicantt",
    },
    {
        "uri": "http://lavalink.clxud.lol:2333",
        "password": "youshallnotpass",
    },
    {
        "uri": "http://45.137.117.104:5124",
        "password": "Jeylani.ทำัคนพืก",
    },
    {
        "uri": "http://37.27.1.113:2333",
        "password": "youshallnotpass",
    },
]


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
        
        emoji_str = str(payload.emoji).replace('\ufe0f', '')
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
        emoji_str = str(payload.emoji).replace('\ufe0f', '')
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


# ========================= MUSIC COG (LAVALINK/WAVELINK) =========================

class Music(commands.Cog):
    """Cog for YouTube music playback using Lavalink"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        """Connect to Lavalink nodes when cog loads"""
        print("[Music] Connecting to Lavalink nodes...")
        
        for i, node_config in enumerate(LAVALINK_NODES):
            try:
                node = wavelink.Node(
                    uri=node_config["uri"],
                    password=node_config["password"],
                )
                await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
                print(f"[Music] ✅ Connected to Lavalink node: {node_config['uri']}")
                return  # Connected successfully, stop trying other nodes
            except Exception as e:
                print(f"[Music] ❌ Failed to connect to node {i+1}: {e}")
                continue
        
        print("[Music] ⚠️ Could not connect to any Lavalink node!")
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"[Music] Lavalink node ready: {payload.node.identifier}")
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        track = payload.track
        
        # Skip if this was triggered by /play command (it already sent the message)
        if hasattr(player, '_skip_next_announce') and player._skip_next_announce:
            player._skip_next_announce = False
            return
        
        # Only send to the stored text channel (where command was used)
        if player and hasattr(player, 'text_channel') and player.text_channel:
            try:
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**{track.title}**",
                    color=discord.Color.purple()
                )
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)
                embed.add_field(name="Duration", value=self.format_duration(track.length), inline=True)
                embed.add_field(name="Author", value=track.author, inline=True)
                await player.text_channel.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if player and not player.queue.is_empty:
            await player.play(player.queue.get())
    
    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        """Disconnect after being inactive"""
        await player.disconnect()
    
    def format_duration(self, ms: int) -> str:
        """Format milliseconds to MM:SS"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="join", description="Join your voice channel")
    async def slash_join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("You must be in a voice channel!", ephemeral=True)
        
        # Defer to prevent timeout during connection
        await interaction.response.defer(thinking=True)
        
        channel = interaction.user.voice.channel
        
        try:
            player = await channel.connect(cls=wavelink.Player, self_deaf=True)
            player.autoplay = wavelink.AutoPlayMode.disabled
            player.text_channel = interaction.channel  # Store for announcements
            await interaction.followup.send(f"✅ Joined **{channel.name}**")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to join: {e}")
    
    @app_commands.command(name="play", description="Play a song from YouTube")
    @app_commands.describe(query="YouTube URL or search query")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        # Defer IMMEDIATELY to prevent timeout
        await interaction.response.defer(thinking=True)
        
        # Clean up query (remove accidental spaces)
        query = query.strip()
        
        # Get or create player
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            if not interaction.user.voice:
                return await interaction.followup.send("You're not in a voice channel!")
            
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
                player.autoplay = wavelink.AutoPlayMode.disabled
            except Exception as e:
                return await interaction.followup.send(f"❌ Failed to join: {e}")
        
        # Store the text channel for announcements
        player.text_channel = interaction.channel
        
        # Search for track
        try:
            # Add ytsearch: prefix if not a URL
            if not query.startswith(('http://', 'https://')):
                query = f"ytsearch:{query}"
            
            tracks = await wavelink.Playable.search(query)
            if not tracks:
                return await interaction.followup.send("❌ No results found!")
            
            track = tracks[0]
            
            if player.playing:
                player.queue.put(track)
                embed = discord.Embed(
                    title="📝 Added to Queue",
                    description=f"**{track.title}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Position", value=f"#{len(player.queue)}", inline=True)
                embed.add_field(name="Duration", value=self.format_duration(track.length), inline=True)
                await interaction.followup.send(embed=embed)
            else:
                # Skip the on_wavelink_track_start announcement (we'll send it here)
                player._skip_next_announce = True
                await player.play(track)
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**{track.title}**",
                    color=discord.Color.purple()
                )
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)
                embed.add_field(name="Duration", value=self.format_duration(track.length), inline=True)
                embed.add_field(name="Author", value=track.author, inline=True)
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")
    
    @app_commands.command(name="skip", description="Skip the current song")
    async def slash_skip(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player or not player.playing:
            return await interaction.response.send_message("Nothing playing.", ephemeral=True)
        
        await player.skip()
        await interaction.response.send_message("⏭️ Skipped!")
    
    @app_commands.command(name="queue", description="View the music queue")
    async def slash_queue(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            return await interaction.response.send_message("Not connected to voice.", ephemeral=True)
        
        embed = discord.Embed(title="📜 Music Queue", color=discord.Color.purple())
        
        # Current track
        if player.current:
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{player.current.title}** ({self.format_duration(player.current.length)})",
                inline=False
            )
        
        # Queue
        if player.queue:
            queue_text = "\n".join([
                f"{i+1}. **{track.title}** ({self.format_duration(track.length)})"
                for i, track in enumerate(list(player.queue)[:10])
            ])
            embed.add_field(name=f"Up Next ({len(player.queue)} songs)", value=queue_text, inline=False)
        else:
            embed.add_field(name="Up Next", value="Queue is empty", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leave", description="Leave the voice channel")
    async def slash_leave(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            return await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
        
        await player.disconnect()
        await interaction.response.send_message("👋 Disconnected!")
    
    @app_commands.command(name="pause", description="Pause the music")
    async def slash_pause(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player or not player.playing:
            return await interaction.response.send_message("Nothing playing.", ephemeral=True)
        
        await player.pause(True)
        await interaction.response.send_message("⏸️ Paused!")
    
    @app_commands.command(name="resume", description="Resume the music")
    async def slash_resume(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            return await interaction.response.send_message("Nothing paused.", ephemeral=True)
        
        await player.pause(False)
        await interaction.response.send_message("▶️ Resumed!")
    
    @app_commands.command(name="volume", description="Set the volume")
    @app_commands.describe(level="Volume level (0-100)")
    async def slash_volume(self, interaction: discord.Interaction, level: int):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            return await interaction.response.send_message("Not connected.", ephemeral=True)
        
        level = max(0, min(100, level))
        await player.set_volume(level)
        await interaction.response.send_message(f"🔊 Volume set to {level}%")
    
    @app_commands.command(name="nowplaying", description="Show current song")
    async def slash_nowplaying(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player or not player.current:
            return await interaction.response.send_message("Nothing playing.", ephemeral=True)
        
        track = player.current
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.purple()
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        
        # Progress bar
        position = player.position
        duration = track.length
        progress = int((position / duration) * 20) if duration > 0 else 0
        bar = "▓" * progress + "░" * (20 - progress)
        
        embed.add_field(
            name="Progress",
            value=f"`{self.format_duration(position)}` {bar} `{self.format_duration(duration)}`",
            inline=False
        )
        embed.add_field(name="Author", value=track.author, inline=True)
        embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="musichelp", description="Show music commands")
    async def slash_musichelp(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎵 Music Commands", color=discord.Color.purple())
        embed.add_field(name="Commands", value="""
`/join` - Join voice channel
`/play <url/search>` - Play a song
`/skip` - Skip current song
`/pause` - Pause playback
`/resume` - Resume playback
`/volume <0-100>` - Set volume
`/queue` - View queue
`/nowplaying` - Show current song
`/leave` - Leave channel
        """, inline=False)
        embed.set_footer(text="Powered by Lavalink 🎶")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ========================= BOT SETUP =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print("=" * 50)
    print(f"Caleb Bot v3 is ready! (Lavalink Edition)")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"Discord.py version: {discord.__version__}")
    print(f"Wavelink version: {wavelink.__version__}")
    print(f"Guilds: {len(bot.guilds)}")
    print("=" * 50)
    
    # Load cogs
    await bot.add_cog(RoleAssignment(bot))
    await bot.add_cog(DrinkCounter(bot))
    await bot.add_cog(Music(bot))
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")
    
    # Set status
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="/play | Lavalink 🎵"
    ))


@bot.event
async def on_voice_state_update(member, before, after):
    """Auto-disconnect when alone in voice channel"""
    if member.id == bot.user.id:
        return
    
    player: wavelink.Player = member.guild.voice_client
    if player and player.channel:
        members = [m for m in player.channel.members if not m.bot]
        if len(members) == 0:
            await player.disconnect()


@bot.command(name="help")
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🤖 Caleb Bot v3 - Help",
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
    
    embed.add_field(name="🎵 Music (Lavalink)", value="""
`/join` `/leave` `/play <url>`
`/skip` `/pause` `/resume` `/queue`
`/volume` `/nowplaying`
    """, inline=False)
    
    embed.set_footer(text="Powered by Lavalink 🎶")
    await ctx.send(embed=embed)


@bot.tree.command(name="help", description="Show all available commands")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Caleb Bot v3 - Help",
        description="All available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🎭 Role Assignment", value="React to role messages to get roles!", inline=False)
    embed.add_field(name="🍻 Drink Counter", value="`/owe` `/paid` `/drinks` `/leaderboard`", inline=False)
    embed.add_field(name="🎵 Music", value="`/join` `/play` `/skip` `/pause` `/resume` `/queue` `/volume` `/nowplaying` `/leave`", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("ERROR: Invalid token!")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
