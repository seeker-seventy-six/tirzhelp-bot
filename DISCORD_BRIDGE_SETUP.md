# Discord-to-Telegram Bridge & Invite Rotation Setup

## Overview
This feature provides **bidirectional bridging** between Discord and Telegram, plus automated Telegram invite rotation:
- **Discord → Telegram**: Links and images from the DISCORD_STGTS channel to a Telegram topic.
- **Telegram → Discord**: Images from that Telegram topic back to DISCORD_STGTS.
- **Telegram Invite Rotation → DISCORD_ROOT**: Periodically generates a batch of fresh Telegram invite links, revokes the old batch (configurable), and replaces the invite message inside the DISCORD_ROOT channel so members always see the latest links.

**Discord STGTS Channel**: #public-test-results-no-discussion  
**Telegram Topic**: Test Results 3P ONLY - No Discussion  
**Discord Root Channel**: Configurable via `DISCORD_ROOT_CHANNEL_ID`

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
3. Select bot permissions: ``View Channels`, `Read Messages`, `Read Message History`, `Send Messages`, `Attach Files`
4. Copy the generated invite URL
5. Open the URL in your browser and select the Discord server to add the bot to
6. Click "Authorize" to add the bot to that server

### 3. Environment Variables
Add to both `.env-dev` and `.env-main`:
```
DISCORD_BOT_TOKEN='your-actual-discord-bot-token'
DISCORD_STGTS_CHANNEL_ID='discord-channel-id-for-stgts-bridge'
DISCORD_ROOT_CHANNEL_ID='discord-channel-id-for-invite-posts'
INVITE_TARGET_CHAT_ID='optional-telegram-chat-id-if-not-supergroup'
INVITE_ROTATION_INTERVAL_HOURS=24
INVITE_ROTATION_BATCH_SIZE=5
INVITE_ROTATION_EXPIRE_DAYS=7
INVITE_ROTATION_REVOKE_PREVIOUS='true'
```

> If `INVITE_TARGET_CHAT_ID` is omitted, the bot defaults to the `SUPERGROUP_ID` defined in `TELEGRAM_CONFIG`.

### 4. Deploy
The bridge will automatically start when the bot is deployed and will:
- **Discord → Telegram**: Monitor Discord channel for messages with links/images and forward to Telegram topic
- **Telegram → Discord**: Monitor Telegram topic for images and forward to Discord channel
- Preserve usernames and format messages appropriately for each platform

## Features
- ✅ **Discord → Telegram**: Bridges messages with links (http/www)
- ✅ **Discord → Telegram**: Bridges image attachments
- ✅ **Telegram → Discord**: Bridges image posts
- ✅ **Telegram Invite Rotation → Discord Root**: Automatically creates fresh Telegram invites, revokes the old batch (configurable), and keeps the DISCORD_ROOT channel updated with a single up-to-date message
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
