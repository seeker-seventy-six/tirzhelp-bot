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
        
        # Check if the update contains 'new_chat_members'
        if "message" in update and "new_chat_member" in update["message"]:
            new_member_id = update["message"]["new_chat_member"]["id"]
            # Send a direct message to the new user
            welcome_message = botfunc.welcome_newbie()
            send_message(new_member_id, welcome_message)
    
        # otherwise, look for specific commands
        elif "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            # Respond to the /newbie command
            if text.startswith("/newbie"):
                welcome_message = botfunc.welcome_newbie()
                send_message(chat_id, welcome_message)

            # Respond to the /newbie command
            if text.startswith("/summarize"):
                summary_message = botfunc.summarize_channel()
                send_message(chat_id, summary_message)

        else:
            return jsonify({"error": "No new_chat_members found"}), 400

        return jsonify({"ok": True})

    except Exception as e:
        # Log the error to check what went wrong
        print(f"Error processing webhook: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500

# Helper function to send a message
def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443)
