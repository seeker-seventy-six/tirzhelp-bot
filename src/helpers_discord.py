import discord
import asyncio
import logging
import os
import requests
from io import BytesIO
from src import helpers_telegram

# Bridge IDs
DISCORD_CHANNEL_ID = 1367945937774706799
TELEGRAM_CHAT_ID = '-1002410577414'
TELEGRAM_TOPIC_ID = '48'

class DiscordBridge(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def on_ready(self):
        logging.info(f'Discord bridge logged in as {self.user}')
        
    async def on_message(self, message):
        if message.author.bot:
            return
            
        if message.channel.id != DISCORD_CHANNEL_ID:
            return
            
        has_content = bool(message.content and ('http' in message.content or 'www.' in message.content))
        has_attachments = bool(message.attachments)
        
        if not (has_content or has_attachments):
            return
            
        try:
            telegram_message = f"🔗 <b>STGTS Discord Bridge</b>\n👤 <b>{message.author.display_name}</b>\n\n"
            
            if message.content:
                telegram_message += f"{message.content}\n\n"
                
            helpers_telegram.send_message(
                TELEGRAM_CHAT_ID, 
                telegram_message, 
                message_thread_id=TELEGRAM_TOPIC_ID
            )
            
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    helpers_telegram.send_image(
                        TELEGRAM_CHAT_ID,
                        image_url=attachment.url,
                        message_thread_id=TELEGRAM_TOPIC_ID,
                        caption=f"📎 {attachment.filename}"
                    )
                    
            logging.info(f"Bridged Discord→Telegram: {message.author.display_name}")
            
        except Exception as e:
            logging.error(f"Failed to bridge Discord message: {e}")
            
    async def send_to_discord(self, username, file_url, filename, caption=None):
        """Send file from Telegram to Discord"""
        try:
            channel = self.get_channel(DISCORD_CHANNEL_ID)
            if not channel:
                logging.error("Discord channel not found")
                return
                
            # Download file
            response = requests.get(file_url)
            response.raise_for_status()
            
            # Create message content
            content = f"📱 **STG Telegram Bridge**\n👤 **{username}**"
            if caption:
                content += f"\n\n{caption}"
                
            # Send to Discord
            file = discord.File(fp=BytesIO(response.content), filename=filename)
            await channel.send(content=content, file=file)
            
            logging.info(f"Bridged Telegram→Discord: {username}")
            
        except Exception as e:
            logging.error(f"Failed to send to Discord: {e}")

# Global client instance
discord_client = None

def start_discord_bridge():
    """Initialize and start the Discord bridge"""
    global discord_client
    
    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        logging.warning("DISCORD_BOT_TOKEN not found, Discord bridge disabled")
        return
        
    intents = discord.Intents.default()
    intents.message_content = True
    
    discord_client = DiscordBridge(intents=intents)
    
    # Run in background thread
    def run_discord():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(discord_client.start(discord_token))
        except Exception as e:
            logging.error(f"Discord bridge error: {e}")
        finally:
            loop.close()
    
    import threading
    discord_thread = threading.Thread(target=run_discord, daemon=True)
    discord_thread.start()
    logging.info("Discord bridge started")

def send_telegram_file_to_discord(username, file_url, filename, caption=None):
    """Send file from Telegram to Discord"""
    global discord_client
    if discord_client:
        asyncio.run_coroutine_threadsafe(
            discord_client.send_to_discord(username, file_url, filename, caption),
            discord_client.loop
        )

def stop_discord_bridge():
    """Stop the Discord bridge"""
    global discord_client
    if discord_client:
        asyncio.create_task(discord_client.close())