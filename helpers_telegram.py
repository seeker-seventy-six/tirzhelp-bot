import bot
import requests
import logging
import sys
from PIL import Image
from io import BytesIO


# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)


### TELEGRAM HELPER FUNCTIONS ###

# Function to check if user is a member of the supergroup
def is_user_in_supergroup(user_id):
    url = f"{bot.TELEGRAM_API_URL}/getChatMember"
    params = {
        'chat_id': bot.TIRZHELP_SUPERGROUP_ID,
        'user_id': user_id
    }
    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code == 200 and 'result' in data:
        status = data['result']['status']
        return status in ['member', 'administrator', 'creator']
    else:
        return False

# Helper function to send a message
def send_message(chat_id, text, message_thread_id=None, reply_to_message_id=None):
    try:
        url = f"{bot.TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if message_thread_id:
            payload['message_thread_id'] = message_thread_id
        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Telegram API returned an error: {response.text}")

            # Check for specific error when `reply_to_message_id` is invalid
            if "Bad Request: message to be replied not found" in response.text:
                logging.warning("Reply message not found. Skipping sending message.")
                return  # Exit the function without sending

            response.raise_for_status()  # Raise for other non-2xx errors

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(f"send_message failed: {e}")
        raise RuntimeError(f"send_message failed: {e}")


# Helper function to send a document or GIF with or without a caption
def send_gif(chat_id, document_url, message_thread_id=None, reply_to_message_id=None, caption=None):
    """
    Sends a document to a Telegram chat.

    Args:
        chat_id (int or str): The chat ID or username to send the document to.
        document_url (str): The URL of the document to send.
        caption (str): An optional caption for the document.
        message_thread_id (int): Optional thread ID (for topics in groups).
        reply_to_message_id (int): Optional message ID to reply to.
    """
    try:
        url = f"{bot.TELEGRAM_API_URL}/sendDocument"
        payload = {
            "chat_id": chat_id,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        # Step 1: Download the .webp file
        response = requests.get(document_url, stream=True)
        response.raise_for_status()
        webp_content = BytesIO(response.content)

        # Step 2: Convert .webp to .gif
        gif_content = BytesIO()
        with Image.open(webp_content) as img:
            img.save(gif_content, format="GIF")
        gif_content.name = "converted.gif"  # Set a name for the file
        gif_content.seek(0)  # Reset the pointer to the start of the file
        files = {"document": gif_content}

        if caption:
            payload['caption'] = caption
        if message_thread_id:
            payload['message_thread_id'] = message_thread_id
        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id

        response = requests.post(url, data=payload, files=files)

        if response.status_code != 200:
            logging.error(f"Telegram API returned an error: {response.text}")

            # Check for specific error when `reply_to_message_id` is invalid
            if "Bad Request: message to be replied not found" in response.text:
                logging.warning("Reply message not found. Skipping sending document.")
                return  # Exit the function without sending

            response.raise_for_status()  # Raise for other non-2xx errors

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(f"send_document failed: {e}")
        raise RuntimeError(f"send_document failed: {e}")

    finally:
        # Ensure file is closed after sending
        if "files" in locals():
            files['document'].close()


# Helper function to pin a message
def pin_message(chat_id, message_id):
    try:
        url = f"{bot.TELEGRAM_API_URL}/pinChatMessage"
        payload = {"chat_id": chat_id, "message_id": message_id}
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Telegram API returned an error: {response.text}")
            response.raise_for_status()  # This raises an exception for non-2xx responses
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logging.error(f"pin_message failed: {e}")
        raise RuntimeError(f"pin_message failed: {e}")