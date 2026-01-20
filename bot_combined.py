"""
Combined Discord Bot - Main entry point
Loads all cogs (RoleAssignment, DrinkCounter, etc.)
Designed for AWS hosting
"""

import discord
from discord.ext import commands
import asyncio
import os

from private import token

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


# List of cog modules to load
COGS = [
    "caleb",      # Role Assignment
    "drink",      # Drink Counter
    # Add more cogs here as needed
]


@bot.event
async def on_ready():
    print("=" * 50)
    print(f"Bot is ready!")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"Discord.py version: {discord.__version__}")
    print(f"Guilds: {len(bot.guilds)}")
    print("=" * 50)
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!drinkhelp | !command"
        )
    )


async def load_cogs():
    """Load all cog modules"""
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")


async def main():
    """Main entry point for the bot"""
    async with bot:
        await load_cogs()
        await bot.start(token())


if __name__ == "__main__":
    asyncio.run(main())
