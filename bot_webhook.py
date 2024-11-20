from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

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
    update = request.get_json()
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        # Respond to the /newbie command
        if text.startswith("/newbie"):
            welcome_message = "🎉 Welcome to the group! Feel free to introduce yourself."
            send_message(chat_id, welcome_message)

    return {"ok": True}

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
