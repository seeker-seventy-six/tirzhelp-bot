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
TIRZHELP_GENERAL_CHANNEL = '13'
TIRZHELP_CLOSED_CHANNLES = ['1','3','19','63']
TIRZHELP_IGNORE_AUTOMOD_CHANNELS = ['59','48']

TEST_SUPERGROUP_ID = '-1002334662710'
TEST_TEST_RESULTS_CHANNEL = '367'
TEST_NEWBIE_CHANNEL = '681'
TEST_GENERAL_CHANNEL = '1'

MOD_ACCOUNTS = [
    'tirzhelp_bot',
    'seekerseventysix',
    'tirzepatidehelp',
    'delululemonade',
    'Steph_S_1975',
    'aksailor',
    'NordicTurtle',
    'Ruca2573',
    'Litajj',
    'UncleNacho'
    'ruttheimer'
]

app = Flask(__name__)

### NON WEBHOOK ###

# def run_ai_conversation_loop():
#     logging.info("🔁 Starting AI murder mystery roleplay thread...")

#     while True:
#         try:
#             logging.info("🎭 Starting new AI exchange round...")
#             # Generate one message (conversation history is tracked internally)
#             exchange, pic_path = generate_ai_conversation()

#             if exchange is None:
#                 logging.info("🔚 All interviews complete. Ending loop.")
#                 break  # Exit cleanly when all personas are done

#             if ENVIRONMENT == 'PROD':
#                 helpers_telegram.send_image(TIRZHELP_SUPERGROUP_ID, pic_path, message_thread_id=TIRZHELP_GENERAL_CHANNEL)
#                 for msg in exchange:
#                     helpers_telegram.send_message(TIRZHELP_SUPERGROUP_ID, msg, message_thread_id=TIRZHELP_GENERAL_CHANNEL)
#                     time.sleep(10)
#             else:
#                 helpers_telegram.send_image(TEST_SUPERGROUP_ID, pic_path)
#                 for msg in exchange:
#                     helpers_telegram.send_message(TEST_SUPERGROUP_ID, msg)
#                     time.sleep(10)
#             # Wait 30 mins
#             time.sleep(1800)

#         except Exception as e:
#             logging.error(f"💥 AI roleplay thread error: {e}")

#     # After the loop exits
#     summary = generate_final_summary()
#     if ENVIRONMENT == 'PROD':
#         helpers_telegram.send_image(TIRZHELP_SUPERGROUP_ID, 'murder_mystery_pics/tirzhelpbot.jpg', TIRZHELP_GENERAL_CHANNEL)
#         helpers_telegram.send_message(TIRZHELP_SUPERGROUP_ID, summary, TIRZHELP_GENERAL_CHANNEL)
#     else:
#         helpers_telegram.send_image(TEST_SUPERGROUP_ID, 'murder_mystery_pics/tirzhelpbot.jpg')
#         helpers_telegram.send_message(TEST_SUPERGROUP_ID, summary)
        
# def start_ai_roleplay_thread():
#     logging.info("Starting murder mystery roleplay...")
#     thread = threading.Thread(target=run_ai_conversation_loop, daemon=True)
#     thread.start()
    

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
    global banned_data, newbies_mod_topics, dont_link_domains, ignore_domains, auto_poof_terms

    # Get banned topics
    with open('./mod_topics/moderated_topics.yml', 'r') as file:
        mod_topics_data = yaml.safe_load(file)
    banned_data = mod_topics_data.get('Banned_Topics', {})
    newbies_mod_topics = mod_topics_data.get('Newbies_Auto_Reply', {})
    
    # Get dont link communities
    with open('./mod_topics/dont_link.yml', 'r') as file:
        domains = yaml.safe_load(file)
    dont_link_domains = domains.get('domain_urls', [])
    ignore_domains = domains.get('ignore_urls', [])

    # Get auto poof terms
    with open('./mod_topics/poof_no_message.yml', 'r') as file:
        poof_data = yaml.safe_load(file)
    auto_poof_terms = poof_data.get('auto-poof', [])
    
    logging.info("Setting global variables...")
    return banned_data, newbies_mod_topics, dont_link_domains, ignore_domains, auto_poof_terms

# Ensure thread is started and globals created on app import
# start_ai_roleplay_thread()
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
    payload = {
        "url": f"{WEBHOOK_URL}",
        "allowed_updates": ["message", "edited_message", "channel_post", "edited_channel_post", "inline_query", "callback_query", "chat_member", "my_chat_member"]
    }
    response = requests.post(url, json=payload)
    return response.json()

# Delete the webhook
@app.route('/deletewebhook', methods=['GET'])
def delete_webhook():
    url = f"{TELEGRAM_API_URL}/deleteWebhook"
    payload = {"url": f"{WEBHOOK_URL}"}
    response = requests.post(url, json=payload)
    return response.json()

# Handle incoming updates
@app.route('/webhook', methods=['POST'])
def webhook():
    global banned_data, newbies_mod_topics, dont_link_domains, ignore_domains, auto_poof_terms
    
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
        message_thread_id = message.get("message_thread_id", 1)
        message_id = message.get("message_id", None)
        user_id = message.get('from', {}).get('id', None)
        user_firstname = message.get('from', {}).get('first_name', None)
        username = message.get('from', {}).get('username', None)
        text = message.get('text', '').strip()

        ### HANDLE COMMANDS ###
        if text.startswith("/"):
            command = text.split()[0].lower()  # Extract the command
            handle_command(command, chat_id, message_thread_id, message_id, update)
            return jsonify({"ok": True}), 200
        
        ### Skip the rest of the Bot functions if update is not from the main moderation TG groups
        if str(chat_id) not in [TIRZHELP_SUPERGROUP_ID, TEST_SUPERGROUP_ID]:
            return jsonify({"ok": True}), 200  # Exit after handling the command for non-target groups
            
        ### AUTOMATED WELCOME MESSAGE FOR NEW MEMBER ###
        # Check for "new_chat_member" in the ChatMemberUpdated update
        if "chat_member" in update:
            chat_member_update = update["chat_member"]
            chat_id = chat_member_update.get("chat", {}).get("id")
            new_member = chat_member_update.get("new_chat_member", {}).get("user")
            new_status = chat_member_update.get("new_chat_member", {}).get("status")
            old_status = chat_member_update.get("old_chat_member", {}).get("status")

            # Check if the user has joined the group
            if new_status == "member" and old_status in ["left", "kicked"]:
                if str(chat_id) in [TIRZHELP_SUPERGROUP_ID, TEST_SUPERGROUP_ID]:
                    welcome_message = msgs.welcome_newbie(new_member.get("id"))
                    helpers_telegram.send_message(chat_id, welcome_message)
                    return jsonify({"ok": True}), 200
        # Check for "new_chat_participant" in the Message update
        if "message" in update and "new_chat_participant" in message:
            if str(chat_id) in [TIRZHELP_SUPERGROUP_ID, TEST_SUPERGROUP_ID]:
                # Here, message_id is the join message's ID.
                welcome_message = msgs.welcome_newbie(message["new_chat_participant"])
                helpers_telegram.send_message(chat_id, welcome_message, reply_to_message_id=message_id)
                return jsonify({"ok": True}), 200
        
        ### ALL OTHER MESSAGES ###
        elif "message" in update:
            ### CHECK FOR BANNED TOPICS ###
            # Iterate through each banned category and their corresponding substances and messages
            for _, data in banned_data.items():
                banned_message = data.get('message')
                banned_topics = data.get('substances')
                # Check for banned topics
                for tuple_topic in banned_topics:
                    for word in tuple_topic:
                        pattern = r'\s' + re.escape(word.lower()) + r'\s'
                        if re.search(pattern, text.lower()):
                            # Pass the tuple_topic and header message to the banned_topic function
                            banned_topic_message = msgs.banned_topic(tuple_topic, banned_message)
                            helpers_telegram.send_message(chat_id, banned_topic_message, message_thread_id, reply_to_message_id=message_id)
                            return jsonify({"ok": True}), 200

            ### CHECK FOR SPECIFIC QUESTIONS IN NEWBIES CHANNEL ###
            if str(message_thread_id) in [TIRZHELP_NEWBIE_CHANNEL, TEST_NEWBIE_CHANNEL] and username not in MOD_ACCOUNTS:
                for topic, data in newbies_mod_topics.items():
                    if any(re.search(pattern, text) for pattern in data["patterns"]):
                        message = data["message"]
                        helpers_telegram.send_message(chat_id, message, message_thread_id, reply_to_message_id=message_id)
                        return jsonify({"ok": True}), 200

            ### AUTO EXTRACT TEST RESULTS ###
            # Respond to uploaded documents in Test Results channel
            if ("document" in message or "photo" in message) and str(message_thread_id) in [TIRZHELP_TEST_RESULTS_CHANNEL, TEST_TEST_RESULTS_CHANNEL]:
                try:
                    test_results_summary = msgs.summarize_test_results(update, BOT_TOKEN)
                    helpers_telegram.send_message(chat_id, test_results_summary, message_thread_id)
                    return jsonify({"ok": True}), 200
                except:
                    helpers_telegram.send_message(chat_id, "🚫 Unsupported file format received. Please check your file is a .pdf, .png, or .jpeg and retry.", message_thread_id)
                    return jsonify({"ok": True}), 200

            ### AUTO POOF LINKED COMMUNITIES ###
            # If the text contains any ignored URL, skip moderation
            if any(ignore_url in text for ignore_url in ignore_domains):
                logging.info("Message contains an ignored URL. No moderation needed.")
                return jsonify({"ok": True}), 200
            # If the text contains any moderated domain, return a warning message
            for moderated_domain in dont_link_domains:
                if moderated_domain in text and username not in MOD_ACCOUNTS:
                    logging.info(f"Detected moderated domain: {moderated_domain}")
                    # Tag the user and reply
                    reply_message = msgs.dont_link(user_id, user_firstname)
                    helpers_telegram.send_message(chat_id, reply_message, message_thread_id)
                    # Delete the posted message
                    helpers_telegram.delete_message(chat_id, message_id)
                    return jsonify({"ok": True}), 200
            
            ### AUTO POOF MESSAGES WITH SPECIFIC TERMS ###
            for term in auto_poof_terms:
                # Using regex with word boundaries to avoid partial matches
                pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                if pattern.search(text) and username not in MOD_ACCOUNTS:
                    if str(message_thread_id) in TIRZHELP_IGNORE_AUTOMOD_CHANNELS:
                        logging.info(f"Message in chat {chat_id} matched auto-poof term '{term}', but skipping deletion due to exempted channel.")
                        break  # Skip deletion but stop further term checking
                    logging.info(f"Auto-poofing message {message_id} in chat {chat_id} for term: {term}")
                    helpers_telegram.delete_message(chat_id, message_id)
                    return jsonify({"ok": True}), 200
        
        # if none of the bot functions need to run, also return success so update is accounted for
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
        try:
            return helpers_telegram.send_message(chat_id, msgs.unsupported(), message_thread_id, reply_to_message_id)
        except:
            return helpers_telegram.send_message(chat_id, msgs.unsupported())


if __name__ == "__main__":
    import argparse

    # Create argument parser
    parser = argparse.ArgumentParser(description="Manage Telegram bot webhooks.")
    parser.add_argument("--delete-webhook", action="store_true", help="Delete the current webhook.")
    parser.add_argument("--set-webhook", action="store_true", help="Set the webhook.")
    
    args = parser.parse_args()

    # Handle delete-webhook
    if args.delete_webhook:
        delete_response = delete_webhook()
        logging.info(f"Delete Webhook Response: {delete_response}")

    # Handle set-webhook
    elif args.set_webhook:
        set_response = set_webhook()
        logging.info(f"Set Webhook Response: {set_response}")

    # If no arguments, start the Flask app
    else:
        app.run(host="0.0.0.0", port=8443)