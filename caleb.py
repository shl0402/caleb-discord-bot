"""
Role Assignment Bot - Assigns roles when users react to specific emojis
Designed as a Cog for easy integration with the main bot
"""

import discord
from discord.ext import commands
from discord import app_commands


class RoleAssignment(commands.Cog):
    """Cog for handling role assignment via emoji reactions"""
    
    # Configuration: Map emoji to role name
    EMOJI_ROLE_MAP = {
        "🕹️": "gamers",
        "🫂": "caleb",
        "💃": "犯人",
        "🤫": "共犯",
        "🐕": "神犬",
    }
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Store message IDs that should trigger role assignment
        # Format: {message_id: channel_id}
        # Note: The bot responds to ANY message with the configured emojis
        # If you want to limit to specific messages, add them here as: {message_id: channel_id}
        self.role_messages: dict[int, int] = {
            1261173511511216231: 0,
            1261157962702127104: 0,
        }
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[RoleAssignment] Cog loaded successfully!")
    
    @commands.command(name="setuproles")
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx: commands.Context):
        """
        Send the role assignment message with all reaction emojis.
        Only administrators can use this command.
        Usage: !setuproles
        """
        embed = discord.Embed(
            title="🎭 Role Assignment",
            description="React to this message to get your role!",
            color=discord.Color.blue()
        )
        
        # Build the role list
        role_list = ""
        for emoji, role_name in self.EMOJI_ROLE_MAP.items():
            role_list += f"{emoji} : {role_name}\n"
        
        embed.add_field(name="Available Roles", value=role_list, inline=False)
        embed.set_footer(text="Click on an emoji to get/remove the corresponding role")
        
        # Send the message
        message = await ctx.send(embed=embed)
        
        # Add all reaction emojis to the message
        for emoji in self.EMOJI_ROLE_MAP.keys():
            await message.add_reaction(emoji)
        
        # Store this message ID for reaction tracking
        self.role_messages[message.id] = ctx.channel.id
        
        print(f"[RoleAssignment] Setup message created: {message.id}")
    
    @commands.command(name="trackroles")
    @commands.has_permissions(administrator=True)
    async def track_roles(self, ctx: commands.Context, message_id: int):
        """
        Add an existing message to role tracking.
        Usage: !trackroles <message_id>
        """
        try:
            message = await ctx.channel.fetch_message(message_id)
            self.role_messages[message.id] = ctx.channel.id
            await ctx.send(f"✅ Now tracking message {message_id} for role reactions!")
        except discord.NotFound:
            await ctx.send("❌ Message not found in this channel!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction add events for role assignment"""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if this is a tracked message or any message with our emojis
        emoji_str = str(payload.emoji)
        
        if emoji_str not in self.EMOJI_ROLE_MAP:
            return
        
        # Get the guild and member
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return
        
        # Get the role name from emoji
        role_name = self.EMOJI_ROLE_MAP[emoji_str]
        
        # Find the role in the guild
        role = discord.utils.get(guild.roles, name=role_name)
        
        if role is None:
            print(f"[RoleAssignment] Role '{role_name}' not found in guild '{guild.name}'")
            return
        
        # Add the role to the member
        try:
            await member.add_roles(role, reason="Role assignment via reaction")
            print(f"[RoleAssignment] Added role '{role_name}' to {member.display_name}")
        except discord.Forbidden:
            print(f"[RoleAssignment] Permission denied to add role '{role_name}'")
        except discord.HTTPException as e:
            print(f"[RoleAssignment] Error adding role: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle reaction remove events for role removal"""
        emoji_str = str(payload.emoji)
        
        if emoji_str not in self.EMOJI_ROLE_MAP:
            return
        
        # Get the guild and member
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return
        
        # Get the role name from emoji
        role_name = self.EMOJI_ROLE_MAP[emoji_str]
        
        # Find the role in the guild
        role = discord.utils.get(guild.roles, name=role_name)
        
        if role is None:
            return
        
        # Remove the role from the member
        try:
            await member.remove_roles(role, reason="Role removal via reaction")
            print(f"[RoleAssignment] Removed role '{role_name}' from {member.display_name}")
        except discord.Forbidden:
            print(f"[RoleAssignment] Permission denied to remove role '{role_name}'")
        except discord.HTTPException as e:
            print(f"[RoleAssignment] Error removing role: {e}")


# Setup function for loading the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(RoleAssignment(bot))


# Standalone run (for testing)
if __name__ == "__main__":
    from private import token
    
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        await bot.add_cog(RoleAssignment(bot))
    
    bot.run(token())
