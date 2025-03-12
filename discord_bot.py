import discord
from discord.ext import commands

TOKEN = "MTM0NzQ0MDA0MzI3NDUzOTA1OQ.GFJwEm.in7TZfJAqucyjLljnRBbK9Iy-cyLXRzWZYYnA8"
GUILD_ID = 1296877428953714778  # Replace with your server ID
MEMBER_ROLE_NAME = "member"  # Replace with the exact role name
EXCLUDED_ROLES = {"Mod", "MEE6"}  # Roles to exclude from assigning member role

# Enable privileged intents
intents = discord.Intents.default()
intents.members = True  # Needed for managing roles
intents.message_content = True  # Needed if reading messages

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Guild not found. Check your GUILD_ID.")
        return
    
    member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
    if not member_role:
        print(f"Role '{MEMBER_ROLE_NAME}' not found.")
        return
    
    mod_roles = {discord.utils.get(guild.roles, name=role) for role in EXCLUDED_ROLES}
    mod_roles.discard(None)  # Remove None values if roles are not found

    updated_count = 0
    for member in guild.members:
        if not any(role in member.roles for role in mod_roles) and member_role not in member.roles:
            try:
                await member.add_roles(member_role)
                print(f"Assigned '{MEMBER_ROLE_NAME}' to {member.name}")
                updated_count += 1
            except discord.Forbidden:
                print(f"Missing permissions to assign role to {member.name}")
            except discord.HTTPException as e:
                print(f"Error assigning role to {member.name}: {e}")
    
    print(f"Finished! Assigned '{MEMBER_ROLE_NAME}' to {updated_count} members.")

bot.run(TOKEN)
