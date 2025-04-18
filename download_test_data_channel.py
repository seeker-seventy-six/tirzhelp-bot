import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto


# Load environment variables
load_dotenv('.env-dev')

# Replace these with your info
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
        if message.reply_to_msg_id != target_topic_id:
            continue  # skip messages not in the desired topic

        if message.media and (isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument))):
            try:
                file_path = await message.download_media(file=DOWNLOAD_DIR)
                print(f"✅ Downloaded: {file_path}")
            except Exception as e:
                print(f"❌ Failed to download message {message.id}: {e}")


if __name__ == '__main__':
    # Check if the script is being run directly
    print("Starting download...")
    # Start the client and run the main function
    with client:
        client.loop.run_until_complete(main())
