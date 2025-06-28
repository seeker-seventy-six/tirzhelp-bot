import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

# Load environment variables
load_dotenv('.env-dev')

# Telegram API credentials
api_id = os.getenv("APP_ID")
api_hash = os.getenv("APP_API_HASH")
phone = os.getenv("PHONE")
target_chat = -1002410577414
target_topic_id = 48

# Where to save files
DOWNLOAD_DIR = 'historic_test_results'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

client = TelegramClient('session_name', api_id, api_hash)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = input("Enter the code you received via Telegram: ")
        await client.sign_in(phone, code)

    print("🔍 Scanning for files in topic ID", target_topic_id)

    entity = await client.get_entity(target_chat)

    async for message in client.iter_messages(entity):
        # This original logic worked for you, keeping as-is:
        if message.reply_to_msg_id != target_topic_id:
            continue

        if message.media and isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
            try:
                # Build base filename from message ID
                base_name = str(message.id)
                if message.file and message.file.name:
                    base_name += f"_{message.file.name}"
                elif isinstance(message.media, MessageMediaPhoto):
                    base_name += ".jpg"
                else:
                    base_name += ".file"

                full_path = os.path.join(DOWNLOAD_DIR, base_name)

                if not os.path.exists(full_path):
                    await message.download_media(file=full_path)
                    print(f"✅ Downloaded: {full_path}")

                    # Save caption/message as .txt (if any)
                    if message.message:
                        text_path = os.path.splitext(full_path)[0] + ".txt"
                        with open(text_path, "w", encoding="utf-8") as f:
                            f.write(message.message)
                        print(f"📝 Saved metadata: {text_path}")

            except Exception as e:
                print(f"❌ Failed to download message {message.id}: {e}")

if __name__ == '__main__':
    print("Starting download...")
    with client:
        client.loop.run_until_complete(main())
