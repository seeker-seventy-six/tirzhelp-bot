from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import logging
import functions as botfunc

# Setup basic logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Load environment variables
load_dotenv()

OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# Set the webhook
@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    url = f"{API_URL}/setWebhook"
    payload = {"url": f"{WEBHOOK_URL}"}
    response = requests.post(url, json=payload)
    return response.json()

# Handle incoming updates
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        logging.debug(f"Received update: {update}")

        if update is None:
            return jsonify({"error": "Invalid JSON format"}), 400
        
        # Check if a new member has joined as 'new_chat_participant'
        if "message" in update and "new_chat_participant" in update["message"]:
            new_member = update["message"]["new_chat_participant"]
            chat_id = update["message"]["chat"]["id"]
            # Send a welcome message when new user joins
            welcome_message = botfunc.welcome_newbie(new_member)
            send_message(chat_id, welcome_message)
    
        # otherwise, look for specific commands made 
        elif "message" in update and "reply_to_message" in update["message"]:
            message = update["message"]
            chat_id = message["chat"]["id"]
            message_thread_id = message["reply_to_message"].get("message_thread_id")
            message_id = message["reply_to_message"].get("message_id")
            text = message.get("text", "")

            # Respond to the /newbie command
            if text.startswith("/newbie"):
                welcome_message = botfunc.welcome_newbie('')
                send_message(chat_id, welcome_message, message_thread_id, reply_to_message_id=message_id)

            # Respond to the /lastcall command
            if text.startswith("/lastcall cost="):
                lastcall_message = botfunc.lastcall(update, BOT_TOKEN)
                response = send_message(chat_id, lastcall_message, message_thread_id)
                try:
                    lastcall_message_id = response['result']['message_id']
                    pin_message(chat_id, lastcall_message_id)
                except:
                    send_message(chat_id, "⚠️ If you would like me to pin this post, I will need Admin rights. Then rerun the command!", message_thread_id)

            # Respond to the /newbie command
            if text.startswith("/summarize"):
                summary_message = botfunc.summarize(update, BOT_TOKEN, OPENAI_TOKEN)
                send_message(chat_id, summary_message, message_thread_id, reply_to_message_id=message_id)

        return jsonify({"ok": True}), 200

    except Exception as e:
        # Log the error to check what went wrong
        logging.debug(f"Error processing webhook: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500


# Helper function to send a message
def send_message(chat_id, text, message_thread_id=None, reply_to_message_id=None):
    url = f"{API_URL}/sendMessage"
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
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to send message: {response.json().get('description', 'Unknown error')}")


# Helper function to pin a message
def pin_message(chat_id, message_id):
    url = f"{API_URL}/pinChatMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to send message: {response.json().get('description', 'Unknown error')}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443)
