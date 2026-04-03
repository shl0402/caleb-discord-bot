import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import os

# Load Discord token from environment variable
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not set!")
    print("Set it with: export DISCORD_TOKEN='your_token_here'")
    exit(1)

# ========================= CONFIGURATION =========================

# Database file path for bot data
DB_PATH = Path(__file__).parent / "caleb_bot_data.db"

# Event Announcement Channel
ANNOUNCEMENT_CHANNEL_ID = 1261146184521875469  # ⚠️ REPLACE THIS WITH YOUR TARGET CHANNEL ID

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
        print(f"[DrinkCounter] Cog loaded!")
    
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


# ========================= EVENT ANNOUNCER COG =========================

class EventAnnouncer(commands.Cog):
    """Cog for managing and announcing events automatically"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
    
    async def cog_load(self):
        await self.init_db()
        self.event_check_loop.start()
        print(f"[EventAnnouncer] Cog loaded! Checking events every 30 minutes.")

    async def cog_unload(self):
        self.event_check_loop.cancel()

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Create base table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS upcoming_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_date TIMESTAMP NOT NULL,
                    event_name TEXT NOT NULL,
                    has_time BOOLEAN NOT NULL,
                    announced_1w BOOLEAN DEFAULT 0,
                    announced_1d BOOLEAN DEFAULT 0
                )
            """)
            
            # Auto-migrate table for new role feature if it doesn't exist
            try:
                await db.execute("ALTER TABLE upcoming_events ADD COLUMN role_mention TEXT")
            except aiosqlite.OperationalError:
                pass # Column already exists, safe to ignore
                
            await db.commit()

    async def parse_and_store_events(self, input_text: str) -> tuple[list, list]:
        """Parses user input text and stores valid events in DB. Returns (success_list, fail_list)"""
        success = []
        failed = []
        
        lines = input_text.strip().split('\n')
        
        async with aiosqlite.connect(self.db_path) as db:
            for line in lines:
                if not line.strip(): continue
                
                try:
                    parts = line.split('|')
                    date_part = parts[0].strip()
                    name_part = parts[1].strip()
                    
                    # Check if a role was provided
                    role_mention = parts[2].strip() if len(parts) > 2 else None
                    
                    has_time = False
                    try:
                        # Try parsing with time first
                        dt = datetime.strptime(date_part, "%m/%d/%Y/%H:%M")
                        has_time = True
                    except ValueError:
                        # Fallback to date only (assume midnight)
                        dt = datetime.strptime(date_part, "%m/%d/%Y")
                    
                    # Prevent adding past events
                    if dt < datetime.now():
                        failed.append(f"{line} (Event is in the past)")
                        continue

                    await db.execute(
                        "INSERT INTO upcoming_events (event_date, event_name, has_time, role_mention) VALUES (?, ?, ?, ?)",
                        (dt.isoformat(), name_part, has_time, role_mention)
                    )
                    
                    role_str = f" [Ping: {role_mention}]" if role_mention else ""
                    success.append(f"✅ **{name_part}** on {dt.strftime('%B %d, %Y' + (' at %H:%M' if has_time else ''))}{role_str}")
                except Exception as e:
                    failed.append(f"❌ `{line}` -> Invalid format")
                    
            await db.commit()
            
        return success, failed

    # ===== VIEW EVENTS =====
    async def get_all_events(self) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM upcoming_events ORDER BY event_date ASC")
            return await cursor.fetchall()

    async def handle_viewevents(self, ctx_or_int):
        events = await self.get_all_events()
        
        if not events:
            embed = discord.Embed(title="📅 Upcoming Events", description="No upcoming events scheduled!", color=discord.Color.blurple())
        else:
            embed = discord.Embed(title="📅 Upcoming Events", color=discord.Color.blurple())
            for event in events:
                dt = datetime.fromisoformat(event['event_date'])
                time_str = dt.strftime('%m/%d/%Y') + (f" at {dt.strftime('%H:%M')}" if event['has_time'] else "")
                role_str = f" [Ping: {event['role_mention']}]" if event['role_mention'] else ""
                
                embed.add_field(
                    name=f"ID: `{event['id']}` | {event['event_name']}",
                    value=f"**Date:** {time_str}{role_str}",
                    inline=False
                )

        if isinstance(ctx_or_int, discord.Interaction):
            await ctx_or_int.response.send_message(embed=embed)
        else:
            await ctx_or_int.send(embed=embed)

    @commands.command(name="viewevents")
    async def prefix_viewevents(self, ctx):
        """List all upcoming events"""
        await self.handle_viewevents(ctx)

    @app_commands.command(name="viewevents", description="List all upcoming events")
    async def slash_viewevents(self, interaction: discord.Interaction):
        await self.handle_viewevents(interaction)

    # ===== ADD EVENT =====
    async def handle_addevent(self, ctx_or_int, events_text: str):
        success, failed = await self.parse_and_store_events(events_text)
        
        embed = discord.Embed(title="📅 Event Addition Results", color=discord.Color.blurple())
        
        if success:
            embed.add_field(name="Successfully Added", value="\n".join(success), inline=False)
        if failed:
            embed.add_field(name="Failed to Add", value="\n".join(failed) + "\n\n*Format: MM/DD/YYYY/HH:MM|Name|@Role*", inline=False)
            
        if not success and not failed:
            embed.description = "No input provided."

        if isinstance(ctx_or_int, discord.Interaction):
            await ctx_or_int.response.send_message(embed=embed)
        else:
            await ctx_or_int.send(embed=embed)

    @commands.command(name="addevent")
    async def prefix_addevent(self, ctx, *, events_text: str):
        """Add events. Use Shift+Enter for multiple events."""
        await self.handle_addevent(ctx, events_text)

    @app_commands.command(name="addevent", description="Add one or multiple events")
    @app_commands.describe(events_text="Format: MM/DD/YYYY/HH:MM | Event Name | @Role (Newlines for multiple)")
    async def slash_addevent(self, interaction: discord.Interaction, events_text: str):
        await self.handle_addevent(interaction, events_text)

    # ===== REMOVE EVENT =====
    async def handle_removeevent(self, ctx_or_int, event_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM upcoming_events WHERE id = ?", (event_id,))
            if cursor.rowcount > 0:
                await db.commit()
                msg = f"✅ Event ID `{event_id}` has been removed successfully!"
            else:
                msg = f"❌ Event ID `{event_id}` not found. Use `/viewevents` to see valid IDs."
                
        if isinstance(ctx_or_int, discord.Interaction):
            await ctx_or_int.response.send_message(msg)
        else:
            await ctx_or_int.send(msg)

    @commands.command(name="removeevent")
    async def prefix_removeevent(self, ctx, event_id: int):
        """Remove an event by its ID"""
        await self.handle_removeevent(ctx, event_id)

    @app_commands.command(name="removeevent", description="Remove an event by its ID")
    @app_commands.describe(event_id="The ID of the event to remove (use /viewevents to find it)")
    async def slash_removeevent(self, interaction: discord.Interaction, event_id: int):
        await self.handle_removeevent(interaction, event_id)

    # ===== EDIT EVENT =====
    async def handle_editevent(self, ctx_or_int, event_id: int, new_data: str):
        try:
            parts = new_data.split('|')
            date_part = parts[0].strip()
            name_part = parts[1].strip()
            role_mention = parts[2].strip() if len(parts) > 2 else None

            has_time = False
            try:
                dt = datetime.strptime(date_part, "%m/%d/%Y/%H:%M")
                has_time = True
            except ValueError:
                dt = datetime.strptime(date_part, "%m/%d/%Y")

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """UPDATE upcoming_events 
                       SET event_date = ?, event_name = ?, has_time = ?, role_mention = ?, announced_1w = 0, announced_1d = 0
                       WHERE id = ?""",
                    (dt.isoformat(), name_part, has_time, role_mention, event_id)
                )
                if cursor.rowcount > 0:
                    await db.commit()
                    role_str = f" [Ping: {role_mention}]" if role_mention else ""
                    msg = f"✅ Event ID `{event_id}` updated to: **{name_part}** on {dt.strftime('%B %d, %Y' + (' at %H:%M' if has_time else ''))}{role_str}"
                else:
                    msg = f"❌ Event ID `{event_id}` not found."
                    
        except Exception as e:
            msg = f"❌ Invalid format! Use: `MM/DD/YYYY/HH:MM|Event Name|@Role`"

        if isinstance(ctx_or_int, discord.Interaction):
            await ctx_or_int.response.send_message(msg)
        else:
            await ctx_or_int.send(msg)

    @commands.command(name="editevent")
    async def prefix_editevent(self, ctx, event_id: int, *, new_data: str):
        """Edit an event. Format: !editevent <id> MM/DD/YYYY/HH:MM | Event Name | @Role"""
        await self.handle_editevent(ctx, event_id, new_data)

    @app_commands.command(name="editevent", description="Edit an existing event by ID")
    @app_commands.describe(
        event_id="The ID of the event to edit",
        new_data="Format: MM/DD/YYYY/HH:MM | Event Name | @Role"
    )
    async def slash_editevent(self, interaction: discord.Interaction, event_id: int, new_data: str):
        await self.handle_editevent(interaction, event_id, new_data)

    # ===== ANNOUNCEMENT LOOP =====
    @tasks.loop(minutes=30)
    async def event_check_loop(self):
        """Background loop to check for upcoming events and post announcements"""
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not channel:
            print(f"[EventAnnouncer] WARNING: Announcement channel {ANNOUNCEMENT_CHANNEL_ID} not found.")
            return

        now = datetime.now()
        updates_made = False

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM upcoming_events WHERE announced_1d = 0")
            events = await cursor.fetchall()
            
            for event in events:
                event_dt = datetime.fromisoformat(event['event_date'])
                time_diff = event_dt - now
                days_left = time_diff.total_seconds() / 86400

                # If event passed without being triggered (e.g. bot was offline), mark it complete
                if days_left < 0:
                    await db.execute("UPDATE upcoming_events SET announced_1w = 1, announced_1d = 1 WHERE id = ?", (event['id'],))
                    updates_made = True
                    continue

                # Prepare the ping message content
                ping_content = event['role_mention'] if event['role_mention'] else None

                # 1 Week Announcement (Between 1 and 7 days left)
                if not event['announced_1w'] and 1 < days_left <= 7:
                    embed = discord.Embed(
                        title="⏳ Upcoming Event in 1 Week!",
                        description=f"**{event['event_name']}** is coming up!",
                        color=discord.Color.gold()
                    )
                    time_str = event_dt.strftime('%A, %B %d, %Y') + (f" at {event_dt.strftime('%H:%M')}" if event['has_time'] else "")
                    embed.add_field(name="Date", value=time_str)
                    
                    await channel.send(content=ping_content, embed=embed)
                    await db.execute("UPDATE upcoming_events SET announced_1w = 1 WHERE id = ?", (event['id'],))
                    updates_made = True

                # 1 Day Announcement (Between 0 and 1 days left)
                elif not event['announced_1d'] and 0 < days_left <= 1:
                    embed = discord.Embed(
                        title="🚨 Event Tomorrow!",
                        description=f"**{event['event_name']}** is happening soon!",
                        color=discord.Color.red()
                    )
                    time_str = event_dt.strftime('%A, %B %d, %Y') + (f" at {event_dt.strftime('%H:%M')}" if event['has_time'] else "")
                    embed.add_field(name="Date", value=time_str)
                    
                    await channel.send(content=ping_content, embed=embed)
                    await db.execute("UPDATE upcoming_events SET announced_1d = 1 WHERE id = ?", (event['id'],))
                    updates_made = True

            if updates_made:
                await db.commit()

        # Clean up old events once a day (run when bot initializes or random cycle)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM upcoming_events WHERE event_date < ?", ((now - timedelta(days=2)).isoformat(),))
            await db.commit()


# ========================= BOT SETUP =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"Caleb Bot v3 is ready! (Event Edition + Roles + Edit/Remove)")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"Discord.py version: {discord.__version__}")
    print(f"Guilds: {len(bot.guilds)}")
    print("=" * 50)
    
    # Load cogs
    await bot.add_cog(RoleAssignment(bot))
    await bot.add_cog(DrinkCounter(bot))
    await bot.add_cog(EventAnnouncer(bot))
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")
    
    # Set status
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="/help | Managing Events 📅"
    ))


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
    
    embed.add_field(name="📅 Event Announcer", value="""
`/viewevents` - See all scheduled events and their IDs
`/addevent` - `MM/DD/YYYY/HH:MM|Event Name|@Role`
`/editevent <id>` - Overwrite an existing event
`/removeevent <id>` - Delete an event
    """, inline=False)
    
    embed.set_footer(text="Bot version 3.3")
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
    embed.add_field(name="📅 Events", value="`/viewevents` `/addevent` `/editevent` `/removeevent`", inline=False)
    
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
