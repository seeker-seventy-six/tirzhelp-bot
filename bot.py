from flask import Flask, request, jsonify
import requests
import threading
import time
import datetime
import re
import os
import sys
import yaml
from dotenv import load_dotenv
import logging

sys.path.append('./src')
from src import create_messages as msgs
from src import helpers_telegram 

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# TELEGRAM IDS
TIRZHELP_SUPERGROUP_ID = '-1002410577414'
TIRZHELP_TEST_RESULTS_CHANNEL = '48'
TIRZHELP_NEWBIE_CHANNEL = '1408'

TEST_SUPERGROUP_ID = '-1002334662710'
TEST_TEST_RESULTS_CHANNEL = '367'
TEST_NEWBIE_CHANNEL = '681'

app = Flask(__name__)

### NON WEBHOOK ###
# Function to send periodic announcements
def start_periodic_announcement():
    while True:
        try:
            now = datetime.datetime.now()
            # Calculate how much time is left until the next hour
            seconds_until_next_hour = 3600 - (now.minute * 60 + now.second)
            # Wait until the next full hour
            time.sleep(seconds_until_next_hour)
            # Replace with your message sending logic
            message = msgs.newbie_announcement()
            if ENVIRONMENT=='PROD':
                helpers_telegram.send_message(TIRZHELP_SUPERGROUP_ID, message, TIRZHELP_NEWBIE_CHANNEL)
                logging.info("Made newbie announcement")
            # else:
            #     helpers_telegram.send_message(TEST_SUPERGROUP_ID, message, TEST_NEWBIE_CHANNEL)
        except Exception as e:
            print(f"Error in announcement thread: {e}")

# Initialize the periodic announcement thread
def initialize_announcement_thread():
    logging.info("Starting periodic announcement thread...")
    thread = threading.Thread(target=start_periodic_announcement, daemon=True)
    thread.start()

# Initialize Global variables
def create_globals():
    global banned_words, pattern, banned_data, dont_link_domains

    # Get banned topics
    with open('./mod_topics/banned_topics.yml', 'r') as file:
        banned_data = yaml.safe_load(file)
    # Flatten all banned topics into a set for O(1) lookups
    banned_words = set()
    for _, data in banned_data.items():
        banned_topics = data.get('substances')
        for topic_list in banned_topics:
            banned_words.update(word.lower() for word in topic_list)
    # Create a single regex pattern for all banned words
    pattern = r'\b(?:' + '|'.join(re.escape(word) for word in banned_words) + r')\b'

    # Get dont link communities
    with open('./mod_topics/dont_link.yml', 'r') as file:
        domains = yaml.safe_load(file)
    dont_link_domains = domains.get('domain_urls', [])
    
    logging.info("Setting global variables...")
    return banned_words, pattern, banned_data, dont_link_domains

# Ensure thread is started and globals created on app import
initialize_announcement_thread()
create_globals()
### NON WEBHOOK END ###


@app.route('/login', methods=['GET'])
def login():
    # The login URL will send the `user_id` parameter (example: ?user_id=123456)
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "No user ID provided"}), 400

    # Check if user is a member of the supergroup
    if helpers_telegram.is_user_in_supergroup(user_id):
        # Allow access (You can generate a session token here)
        return jsonify({"status": "success", "message": "User is authorized"})
    else:
        # Deny access
        return jsonify({"status": "error", "message": "User is not a member of the supergroup"}), 403

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
    global banned_words, pattern, banned_data, dont_link_domains
    
    # Log raw request data
    raw_data = request.data.decode('utf-8')
    logging.info(f"Raw request data: {raw_data}")
    
    try:
        update = request.get_json()
        if update is None:
            return jsonify({"error": "Invalid JSON format"}), 400
            
        ### EXTRACT TG UPDATE IDs ###
        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id', None)
        message_thread_id = message.get("message_thread_id", None)
        message_id = message.get("message_id", None)
        user_id = message.get('from', {}).get('id', None)
        text = message.get("text", "").strip()

        ### HANDLE COMMANDS ###
        if text.startswith("/"):
            command = text.split()[0].lower()  # Extract the command
            handle_command(command, chat_id, message_thread_id, message_id, update)
            return jsonify({"ok": True}), 200
        
        ### Skip the rest of the Bot functions if update is not from the main moderation TG groups
        if str(chat_id) not in [TIRZHELP_SUPERGROUP_ID, TEST_SUPERGROUP_ID]:
            return jsonify({"ok": True}), 200  # Exit after handling the command for non-target groups

        ### AUTOMATED WELCOME MESSAGE FOR NEW MEMBER ###
        if "message" in update and "new_chat_participant" in message:
            new_member = message["new_chat_participant"]
            if str(chat_id) in [TIRZHELP_SUPERGROUP_ID,TEST_SUPERGROUP_ID]:
                welcome_message = msgs.welcome_newbie(new_member)
                helpers_telegram.send_message(chat_id, welcome_message)
                return jsonify({"ok": True}), 200
        
        elif "message" in update:
            ### CHECK FOR BANNED TOPICS ###
            # Check if any banned word exists in the text
            if re.search(pattern, text.lower()):
                # Find which banned topic triggered the message (optional)
                for _, data in banned_data.items():
                    banned_message = data.get('message')
                    banned_topics = data.get('substances')
                    for topic_list in banned_topics:
                        if any(word.lower() in banned_words for word in topic_list):
                            banned_topic_message = msgs.banned_topic(topic_list, banned_message)
                            helpers_telegram.send_message(chat_id, banned_topic_message, message_thread_id, reply_to_message_id=message_id)
                            return jsonify({"ok": True}), 200

            ### AUTO REMOVE LINKED COMMUNITIES TWMNBN ###
            for domain in dont_link_domains:
                # Create the domain regex pattern to detect the domain in the text
                pattern = r'\b(?:' + re.escape(domain) + r')\b'
                if re.search(pattern, text.lower()):
                    # Tag the user and reply
                    reply_message = msgs.dont_link(user_id)
                    helpers_telegram.send_message(chat_id, reply_message, message_thread_id)
                    # Delete the posted message
                    helpers_telegram.delete_message(chat_id, message_id)
                    return jsonify({"ok": True}), 200           

            ### CHECK FOR SPECIFIC QUESTIONS IN NEWBIES CHANNEL ###
            amo_patterns = [r"\sL\d{2}.*\?", r"L\s\d{2}.*\?", r"Amo.*L.*\?"]
            qsc_patterns = [r"QSC", r"qsc"]
            # Check if the message contains any Amo-related pattern
            if any(re.search(pattern, text) for pattern in amo_patterns) and str(message_thread_id) in [TIRZHELP_NEWBIE_CHANNEL, TEST_NEWBIE_CHANNEL]:
                message = msgs.amo_L_question()
                helpers_telegram.send_message(chat_id, message, message_thread_id, reply_to_message_id=message_id)
                return jsonify({"ok": True}), 200
            
            # Autoreply for QSC mentions in Newbies
            if any(re.search(pattern, text) for pattern in qsc_patterns) and str(message_thread_id) in [TIRZHELP_NEWBIE_CHANNEL, TEST_NEWBIE_CHANNEL]:
                message = msgs.qsc_question()
                helpers_telegram.send_message(chat_id, message, message_thread_id, reply_to_message_id=message_id)
                return jsonify({"ok": True}), 200
    
            ### AUTO EXTRACT TEST RESULTS ###
            # Respond to uploaded documents in Test Results channel
            if ("document" in message or "photo" in message) and str(message_thread_id) in [TIRZHELP_TEST_RESULTS_CHANNEL, TEST_TEST_RESULTS_CHANNEL]:
                test_results_summary = msgs.summarize_test_results(update, BOT_TOKEN)
                helpers_telegram.send_message(chat_id, test_results_summary, message_thread_id)
                return jsonify({"ok": True}), 200

    except Exception as e:
        # Log the error to check what went wrong
        logging.error(f"Error processing webhook: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500


# Helper to handle commands
def handle_command(command, chat_id, message_thread_id, reply_to_message_id, update):
    command_dispatcher = {
        "/newbie": lambda: helpers_telegram.send_message(
            chat_id, msgs.welcome_newbie(''), message_thread_id, reply_to_message_id
        ),
        "/lastcall": lambda: helpers_telegram.send_message(
            chat_id, msgs.lastcall(update, BOT_TOKEN), message_thread_id, reply_to_message_id
        ),
        "/safety": lambda: helpers_telegram.send_message(
            chat_id, msgs.safety(), message_thread_id, reply_to_message_id
        ),
    }
    if command in command_dispatcher:
        return command_dispatcher[command]()
    else:
        return helpers_telegram.send_message(chat_id, msgs.unsupported(), message_thread_id, reply_to_message_id)


if __name__ == "__main__":
    # Start the Flask app for web workers
    app.run(host="0.0.0.0", port=8443)
    