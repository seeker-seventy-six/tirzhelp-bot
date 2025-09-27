import discord
import asyncio
import logging
import os
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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
            
            # Send attachments
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    helpers_telegram.send_image(
                        TELEGRAM_CHAT_ID,
                        image_url=attachment.url,
                        message_thread_id=TELEGRAM_TOPIC_ID,
                        caption=f"📎 {attachment.filename}"
                    )
            
            # Extract and send images from links if no attachments
            if not message.attachments and has_content:
                await self.extract_and_send_link_images(message.content)
                    
            logging.info(f"Bridged Discord→Telegram: {message.author.display_name}")
            
        except Exception as e:
            logging.error(f"Failed to bridge Discord message: {e}")
            
    async def extract_and_send_link_images(self, content):
        """Extract images from webpage links and send to Telegram"""
        import re
        
        # Find URLs in content
        urls = re.findall(r'https?://[^\s]+', content)
        
        for url in urls:
            try:
                response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for images with priority order
                image_url = None
                
                # 1. Try report-specific images first
                report_img = soup.find('img', class_='report-img') or soup.find('img', alt=lambda x: x and 'test report' in x.lower())
                if report_img and report_img.get('src'):
                    image_url = report_img['src']
                
                # 2. Try Open Graph image
                if not image_url:
                    og_image = soup.find('meta', property='og:image')
                    if og_image and og_image.get('content'):
                        image_url = og_image['content']
                
                # 3. Try first img tag
                if not image_url:
                    img_tag = soup.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                
                # Make URL absolute
                if image_url:
                    image_url = urljoin(url, image_url)
                    
                    # Send image to Telegram
                    helpers_telegram.send_image(
                        TELEGRAM_CHAT_ID,
                        image_url=image_url,
                        message_thread_id=TELEGRAM_TOPIC_ID,
                        caption=f"🔗 From: {image_url}"
                    )
                    break  # Only send first image found
                    
            except Exception as e:
                logging.error(f"Failed to extract image from {url}: {e}")
                continue
            
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