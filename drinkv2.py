"""
Drink Counter Bot - Tracks who owes who a drink
Designed as a Cog for easy integration with the main bot
Uses SQLite for persistent storage (lightweight, serverless - perfect for AWS)
Each channel has its own separate leaderboard!
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from pathlib import Path
from datetime import datetime


# Database file path
DB_PATH = Path(__file__).parent / "drink_counter.db"


class DrinkCounter(commands.Cog):
    """Cog for tracking drink debts between users (per-channel)"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
    
    async def cog_load(self):
        """Called when the cog is loaded - initialize database"""
        await self.init_db()
        print(f"[DrinkCounter] Cog loaded! Database: {self.db_path}")
    
    async def init_db(self):
        """Initialize the SQLite database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Drop old table if exists and create new one with channel_id
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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS drink_history_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    debtor_id INTEGER NOT NULL,
                    creditor_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def add_drink_debt(self, guild_id: int, channel_id: int, debtor_id: int, 
                             creditor_id: int, amount: int = 1, reason: str = None) -> int:
        """Add drink debt (debtor owes creditor) - per channel"""
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
            
            await db.execute(
                "INSERT INTO drink_history_v2 (guild_id, channel_id, debtor_id, creditor_id, amount, action, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (guild_id, channel_id, debtor_id, creditor_id, amount, "ADD", reason)
            )
            
            await db.commit()
            return new_amount
    
    async def pay_drink_debt(self, guild_id: int, channel_id: int, debtor_id: int, 
                             creditor_id: int, amount: int = 1) -> tuple[bool, int]:
        """Pay off drink debt. Returns (success, remaining_amount)"""
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
            
            await db.execute(
                "INSERT INTO drink_history_v2 (guild_id, channel_id, debtor_id, creditor_id, amount, action) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, channel_id, debtor_id, creditor_id, amount, "PAY")
            )
            
            await db.commit()
            return True, new_amount
    
    async def get_user_debts(self, guild_id: int, channel_id: int, user_id: int) -> dict:
        """Get all debts for a user in a specific channel"""
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
        """Get all debts in a channel"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT debtor_id, creditor_id, amount FROM drink_debts_v2 WHERE guild_id = ? AND channel_id = ? AND amount > 0 ORDER BY amount DESC",
                (guild_id, channel_id)
            )
            return await cursor.fetchall()
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[DrinkCounter] Ready!")

    # ==================== PREFIX COMMANDS ====================
    
    @commands.command(name="owe")
    async def cmd_owe(self, ctx: commands.Context, debtor: discord.Member, 
                      creditor: discord.Member, amount: int = 1, *, reason: str = None):
        """
        Record that someone owes a drink.
        Usage: !owe @debtor @creditor [amount] [reason]
        """
        if debtor == creditor:
            await ctx.send("❌ A person can't owe themselves a drink!")
            return
        
        if amount <= 0 or amount > 100:
            await ctx.send("❌ Amount must be between 1 and 100!")
            return
        
        new_total = await self.add_drink_debt(ctx.guild.id, ctx.channel.id, debtor.id, creditor.id, amount, reason)
        
        emoji = "🍺" if amount == 1 else "🍻"
        reason_text = f"\n📝 Reason: {reason}" if reason else ""
        
        embed = discord.Embed(
            title=f"{emoji} Drink Debt Added!",
            description=f"**{debtor.display_name}** now owes **{creditor.display_name}** {new_total} drink(s)!{reason_text}",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"#{ctx.channel.name} • Added by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="paid")
    async def cmd_paid(self, ctx: commands.Context, debtor: discord.Member, 
                       creditor: discord.Member, amount: int = 1):
        """
        Record that a drink debt has been paid.
        Usage: !paid @debtor @creditor [amount]
        """
        success, remaining = await self.pay_drink_debt(ctx.guild.id, ctx.channel.id, debtor.id, creditor.id, amount)
        
        if not success:
            await ctx.send(f"❌ {debtor.display_name} doesn't owe {creditor.display_name} any drinks in this channel!")
            return
        
        if remaining == 0:
            embed = discord.Embed(
                title="✅ Debt Cleared!",
                description=f"**{debtor.display_name}** has paid off their debt to **{creditor.display_name}**! 🎉",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title="🍺 Drink Paid!",
                description=f"**{debtor.display_name}** paid {amount} drink(s) to **{creditor.display_name}**.\nRemaining: {remaining} drink(s)",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
        
        embed.set_footer(text=f"#{ctx.channel.name} • Recorded by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="drinks")
    async def cmd_drinks(self, ctx: commands.Context, user: discord.Member = None):
        """
        Check drink status for yourself or another user in this channel.
        Usage: !drinks [@user]
        """
        target = user or ctx.author
        debts = await self.get_user_debts(ctx.guild.id, ctx.channel.id, target.id)
        
        embed = discord.Embed(
            title=f"🍻 Drink Status: {target.display_name}",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        if debts["owes"]:
            owes_text = ""
            total_owes = 0
            for creditor_id, amount in debts["owes"]:
                member = ctx.guild.get_member(creditor_id)
                name = member.display_name if member else f"Unknown"
                owes_text += f"• {name}: {amount} 🍺\n"
                total_owes += amount
            embed.add_field(name=f"📤 Owes ({total_owes} total)", value=owes_text, inline=False)
        else:
            embed.add_field(name="📤 Owes", value="Nobody! 🎉", inline=False)
        
        if debts["owed"]:
            owed_text = ""
            total_owed = 0
            for debtor_id, amount in debts["owed"]:
                member = ctx.guild.get_member(debtor_id)
                name = member.display_name if member else f"Unknown"
                owed_text += f"• {name}: {amount} 🍺\n"
                total_owed += amount
            embed.add_field(name=f"📥 Is Owed ({total_owed} total)", value=owed_text, inline=False)
        else:
            embed.add_field(name="📥 Is Owed", value="Nobody owes them drinks", inline=False)
        
        embed.set_footer(text=f"#{ctx.channel.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard")
    async def cmd_leaderboard(self, ctx: commands.Context):
        """
        Show all drink debts in this channel.
        Usage: !leaderboard
        """
        debts = await self.get_all_debts(ctx.guild.id, ctx.channel.id)
        
        if not debts:
            embed = discord.Embed(
                title="🍻 Drink Leaderboard",
                description="No drink debts recorded in this channel! 🎉",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"#{ctx.channel.name}")
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🍻 Drink Leaderboard",
            description="All outstanding drink debts:",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        debt_text = ""
        for i, debt in enumerate(debts[:15], 1):
            debtor = ctx.guild.get_member(debt["debtor_id"])
            creditor = ctx.guild.get_member(debt["creditor_id"])
            debtor_name = debtor.display_name if debtor else "Unknown"
            creditor_name = creditor.display_name if creditor else "Unknown"
            debt_text += f"{i}. **{debtor_name}** → **{creditor_name}**: {debt['amount']} 🍺\n"
        
        embed.add_field(name="Debts", value=debt_text, inline=False)
        embed.set_footer(text=f"#{ctx.channel.name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="drinkhelp")
    async def cmd_drinkhelp(self, ctx: commands.Context):
        """Show help for drink commands"""
        embed = discord.Embed(
            title="🍻 Drink Counter Help",
            description="Track who owes who drinks!\n**Each channel has its own separate leaderboard!**",
            color=discord.Color.blue()
        )
        
        commands_list = """
`/owe @debtor @creditor [amount] [reason]` - Record a debt
`/paid @debtor @creditor [amount]` - Record a payment
`/drinks [@user]` - Check drink status
`/leaderboard` - Show all debts in this channel
        """
        
        embed.add_field(name="Commands", value=commands_list, inline=False)
        embed.set_footer(text="Default amount is 1 drink • Use slash commands!")
        
        await ctx.send(embed=embed)

    # ==================== SLASH COMMANDS ====================
    
    @app_commands.command(name="owe", description="Record that someone owes another person a drink")
    @app_commands.describe(
        debtor="The person who owes the drink",
        creditor="The person who is owed the drink",
        amount="Number of drinks (default: 1)",
        reason="Reason for the debt (optional)"
    )
    async def slash_owe(self, interaction: discord.Interaction, debtor: discord.Member, 
                        creditor: discord.Member, amount: int = 1, reason: str = None):
        if debtor == creditor:
            await interaction.response.send_message("❌ A person can't owe themselves a drink!", ephemeral=True)
            return
        
        if amount <= 0 or amount > 100:
            await interaction.response.send_message("❌ Amount must be between 1 and 100!", ephemeral=True)
            return
        
        new_total = await self.add_drink_debt(interaction.guild.id, interaction.channel.id, 
                                               debtor.id, creditor.id, amount, reason)
        
        emoji = "🍺" if amount == 1 else "🍻"
        reason_text = f"\n📝 Reason: {reason}" if reason else ""
        
        embed = discord.Embed(
            title=f"{emoji} Drink Debt Added!",
            description=f"**{debtor.display_name}** now owes **{creditor.display_name}** {new_total} drink(s)!{reason_text}",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"#{interaction.channel.name} • Added by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="paid", description="Record that a drink debt has been paid")
    @app_commands.describe(
        debtor="The person who paid",
        creditor="The person who was paid",
        amount="Number of drinks paid (default: 1)"
    )
    async def slash_paid(self, interaction: discord.Interaction, debtor: discord.Member, 
                         creditor: discord.Member, amount: int = 1):
        success, remaining = await self.pay_drink_debt(interaction.guild.id, interaction.channel.id,
                                                        debtor.id, creditor.id, amount)
        
        if not success:
            await interaction.response.send_message(
                f"❌ {debtor.display_name} doesn't owe {creditor.display_name} any drinks in this channel!", 
                ephemeral=True
            )
            return
        
        if remaining == 0:
            embed = discord.Embed(
                title="✅ Debt Cleared!",
                description=f"**{debtor.display_name}** has paid off their debt to **{creditor.display_name}**! 🎉",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title="🍺 Drink Paid!",
                description=f"**{debtor.display_name}** paid {amount} drink(s) to **{creditor.display_name}**.\nRemaining: {remaining} drink(s)",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
        
        embed.set_footer(text=f"#{interaction.channel.name} • Recorded by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="drinks", description="Check drink status for yourself or another user")
    @app_commands.describe(user="The user to check (default: yourself)")
    async def slash_drinks(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        debts = await self.get_user_debts(interaction.guild.id, interaction.channel.id, target.id)
        
        embed = discord.Embed(
            title=f"🍻 Drink Status: {target.display_name}",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        if debts["owes"]:
            owes_text = ""
            total_owes = 0
            for creditor_id, amount in debts["owes"]:
                member = interaction.guild.get_member(creditor_id)
                name = member.display_name if member else f"Unknown"
                owes_text += f"• {name}: {amount} 🍺\n"
                total_owes += amount
            embed.add_field(name=f"📤 Owes ({total_owes} total)", value=owes_text, inline=False)
        else:
            embed.add_field(name="📤 Owes", value="Nobody! 🎉", inline=False)
        
        if debts["owed"]:
            owed_text = ""
            total_owed = 0
            for debtor_id, amount in debts["owed"]:
                member = interaction.guild.get_member(debtor_id)
                name = member.display_name if member else f"Unknown"
                owed_text += f"• {name}: {amount} 🍺\n"
                total_owed += amount
            embed.add_field(name=f"📥 Is Owed ({total_owed} total)", value=owed_text, inline=False)
        else:
            embed.add_field(name="📥 Is Owed", value="Nobody owes them drinks", inline=False)
        
        embed.set_footer(text=f"#{interaction.channel.name}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="Show all drink debts in this channel")
    async def slash_leaderboard(self, interaction: discord.Interaction):
        debts = await self.get_all_debts(interaction.guild.id, interaction.channel.id)
        
        if not debts:
            embed = discord.Embed(
                title="🍻 Drink Leaderboard",
                description="No drink debts recorded in this channel! 🎉",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"#{interaction.channel.name}")
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title="🍻 Drink Leaderboard",
            description="All outstanding drink debts:",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        debt_text = ""
        for i, debt in enumerate(debts[:15], 1):
            debtor = interaction.guild.get_member(debt["debtor_id"])
            creditor = interaction.guild.get_member(debt["creditor_id"])
            debtor_name = debtor.display_name if debtor else "Unknown"
            creditor_name = creditor.display_name if creditor else "Unknown"
            debt_text += f"{i}. **{debtor_name}** → **{creditor_name}**: {debt['amount']} 🍺\n"
        
        embed.add_field(name="Debts", value=debt_text, inline=False)
        embed.set_footer(text=f"#{interaction.channel.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="drinkhelp", description="Show help for drink commands")
    async def slash_drinkhelp(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🍻 Drink Counter Help",
            description="Track who owes who drinks!\n**Each channel has its own separate leaderboard!**",
            color=discord.Color.blue()
        )
        
        commands_list = """
`/owe @debtor @creditor [amount] [reason]` - Record a debt
`/paid @debtor @creditor [amount]` - Record a payment
`/drinks [@user]` - Check drink status
`/leaderboard` - Show all debts in this channel
        """
        
        embed.add_field(name="Commands", value=commands_list, inline=False)
        embed.set_footer(text="Default amount is 1 drink")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Setup function for loading the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(DrinkCounter(bot))


# Standalone run (for testing)
if __name__ == "__main__":
    from private import token
    
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        await bot.add_cog(DrinkCounter(bot))
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    bot.run(token())
