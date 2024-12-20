from flask import Flask, request, jsonify
import requests
from PIL import Image
from io import BytesIO
import re
import os
import sys
from dotenv import load_dotenv
import logging
import create_messages as botfunc

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# Set the webhook
@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook"
    payload = {"url": f"{WEBHOOK_URL}"}
    response = requests.post(url, json=payload)
    return response.json()

# Handle incoming updates
@app.route('/webhook', methods=['POST'])
def webhook():
    # Log raw request data
    raw_data = request.data.decode('utf-8')
    logging.info(f"Raw request data: {raw_data}")
    try:
        update = request.get_json()
        if update is None:
            return jsonify({"error": "Invalid JSON format"}), 400
        
        # Check if a new member has joined as 'new_chat_participant'
        if "message" in update and "new_chat_participant" in update["message"]:
            new_member = update["message"]["new_chat_participant"]
            chat_id = update["message"]["chat"]["id"]
            # only for the main tirzhelp supergroup chat, post automated join welcome messages
            if str(chat_id) in ['-1002462675990', '-1002334662710']:
                # Send a welcome message when new user joins
                welcome_message = botfunc.welcome_newbie(new_member)
                send_message(chat_id, welcome_message)
    
        # otherwise, look for specific commands made 
        elif "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            message_thread_id = message.get("message_thread_id", None)
            message_id = message.get("message_id", None)
            text = message.get("text", "")

            # Respond to the /newbie command
            if text.lower().startswith("/newbie"):
                welcome_message = botfunc.welcome_newbie('')
                send_message(chat_id, welcome_message, message_thread_id, reply_to_message_id=message_id)

            # Respond to the /lastcall command
            if text.lower().startswith("/lastcall"):
                lastcall_message = botfunc.lastcall(update, BOT_TOKEN)
                send_message(chat_id, lastcall_message, message_thread_id)

            # Respond to the /newbie command
            if text.lower().startswith("/safety"):
                safety_message = botfunc.safety()
                send_message(chat_id, safety_message, message_thread_id)

            # Check for banned topics
            banned_topics = [('DNP','Dinitrophenol')] 
            for tuple_topic in banned_topics:
                for word in tuple_topic:
                    # Use a regular expression to match the word as a whole word
                    pattern = r'\b' + re.escape(word.lower()) + r'\b'
                    if re.search(pattern, text.lower()):
                        # Pass the entire tuple to botfunc
                        banned_topic_message = botfunc.banned_topic(tuple_topic)
                        send_message(chat_id, banned_topic_message, message_thread_id)

            # Respond to uploaded document in Test Results channel
            if ("document" in message or "photo" in message) and str(message_thread_id) in ['4','367']:
                test_results_summary = botfunc.summarize_test_results(update, BOT_TOKEN)
                send_message(chat_id, test_results_summary, message_thread_id)

            # Respond to any other / command which at this point is un supported
            if text.lower().startswith("/"):
                unsupported_message = botfunc.unsupported()
                document_path = "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExbTB6M2xqdWhoMmxud3JoNHhlcTRhcHkxOHY4cXlpcXM0cGIxcnRmZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ZSSoLmkYURcWqKFdVA/giphy.webp"
                send_document(chat_id, document_path, message_thread_id, caption=unsupported_message)

        return jsonify({"ok": True}), 200

    except Exception as e:
        # Log the error to check what went wrong
        logging.error(f"Error processing webhook: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500


# Helper function to send a message
def send_message(chat_id, text, message_thread_id=None, reply_to_message_id=None):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
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
            response.raise_for_status()  # This raises an exception for non-2xx responses
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logging.error(f"send_message failed: {e}")
        raise RuntimeError(f"send_message failed: {e}")

# Helper function to send a docuemnt or gif with or without a caption
def send_document(chat_id, document_url, message_thread_id=None, caption=None):
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
        url = f"{TELEGRAM_API_URL}/sendDocument"
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

        response = requests.post(url, data=payload, files=files)

        if response.status_code != 200:
            logging.error(f"Telegram API returned an error: {response.text}")
            response.raise_for_status()  # This raises an exception for non-2xx responses
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
        url = f"{TELEGRAM_API_URL}/pinChatMessage"
        payload = {"chat_id": chat_id, "message_id": message_id}
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Telegram API returned an error: {response.text}")
            response.raise_for_status()  # This raises an exception for non-2xx responses
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logging.error(f"pin_message failed: {e}")
        raise RuntimeError(f"pin_message failed: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443)
