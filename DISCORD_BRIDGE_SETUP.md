# Discord-to-Telegram Bridge Setup

## Overview
This feature provides **bidirectional bridging** between Discord and Telegram:
- **Discord → Telegram**: Links and images from Discord channel to Telegram topic
- **Telegram → Discord**: Images from Telegram topic to Discord channel

**Discord Channel**: https://discord.com/channels/1351746139325595748/1367945937774706799
**Telegram Topic**: https://web.telegram.org/a/#-1002410577414_48

## Setup Instructions

### 1. Create Discord Bot
1. Go to https://discord.com/developers/applications
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token and add it to your environment variables
5. Enable "Message Content Intent" under Privileged Gateway Intents

### 2. Add Bot to Discord Server
1. Go to "OAuth2" > "URL Generator"
2. Select scopes: `bot`
3. Select bot permissions: `Read Messages`, `Read Message History`, `Send Messages`, `Attach Files`
4. Copy the generated invite URL
5. Open the URL in your browser and select the Discord server that contains channel ID `1367945937774706799`
6. Click "Authorize" to add the bot to that server

### 3. Environment Variables
Add to both `.env-dev` and `.env-main`:
```
DISCORD_BOT_TOKEN='your-actual-discord-bot-token'
```

### 4. Deploy
The bridge will automatically start when the bot is deployed and will:
- **Discord → Telegram**: Monitor Discord channel for messages with links/images and forward to Telegram topic
- **Telegram → Discord**: Monitor Telegram topic for images and forward to Discord channel
- Preserve usernames and format messages appropriately for each platform

## Features
- ✅ **Discord → Telegram**: Bridges messages with links (http/www)
- ✅ **Discord → Telegram**: Bridges image attachments
- ✅ **Telegram → Discord**: Bridges image posts
- ✅ Preserves usernames from both platforms
- ✅ Formats messages appropriately for each platform
- ✅ Runs in background thread
- ✅ Error handling and logging

## File Structure
```
src/
├── helpers_discord.py    # Discord bridge implementation
├── helpers_telegram.py   # Telegram helper functions (existing)
└── ...
```