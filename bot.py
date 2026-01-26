from flask import Flask, request, jsonify
import requests
import threading
import time
import datetime
import re
import unicodedata
import os
import sys
import yaml
import json
from dotenv import load_dotenv
import logging

sys.path.append('./src')
from src import create_messages as msgs
from src import helpers_telegram
from src import helpers_discord 
from src import helpers_invites

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Load environment variables
ENV_FILE = ".env-dev"
if os.path.exists(ENV_FILE):
    logging.info(f"Loading environment variables from {ENV_FILE}")
    load_dotenv(ENV_FILE, override=True)
else:
    logging.info("No local env file found; relying on OS / Heroku env vars.")

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT")
TELEGRAM_CONFIG_JSON = os.getenv("TELEGRAM_CONFIG")
TEST_RESULTS_SPREADSHEET = os.getenv("TEST_RESULTS_SPREADSHEET")
DISCORD_STGTS = os.getenv("DISCORD_STGTS")
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")

if not TELEGRAM_CONFIG_JSON:
    raise RuntimeError("TELEGRAM_CONFIG env var is not set. Please set it to a JSON string with Telegram IDs and accounts.")
try:
    TELEGRAM_CONFIG = json.loads(TELEGRAM_CONFIG_JSON)
except json.JSONDecodeError as exc:
    raise RuntimeError(f"Invalid TELEGRAM_CONFIG JSON: {exc}") from exc


def _require_value(key: str):
    if key not in TELEGRAM_CONFIG:
        raise RuntimeError(f"Missing '{key}' in TELEGRAM_CONFIG")
    return TELEGRAM_CONFIG[key]


def _require_list(key: str):
    value = _require_value(key)
    if not isinstance(value, list):
        raise RuntimeError(f"'{key}' must be a list in TELEGRAM_CONFIG")
    return value


TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUPERGROUP_ID = str(_require_value("SUPERGROUP_ID"))
TEST_RESULTS_CHANNEL = str(_require_value("TEST_RESULTS_CHANNEL"))
GROUP_TEST_CHANNEL = str(_require_value("GROUP_TEST_CHANNEL"))
NEWBIE_CHANNEL = str(_require_value("NEWBIE_CHANNEL"))
GENERAL_CHANNEL = str(_require_value("GENERAL_CHANNEL"))
IGNORE_AUTOMOD_CHANNELS = [str(channel) for channel in _require_list("IGNORE_AUTOMOD_CHANNELS")]
MOD_ACCOUNTS = [str(account) for account in TELEGRAM_CONFIG.get("MOD_ACCOUNTS", [])]
RULES_GUIDE_POST = str(_require_value("RULES_GUIDE_POST"))

app = Flask(__name__)

def start_periodic_announcement(frequency_minutes=180):
    """
    Post the newbie announcement on a clean N-minute cadence (e.g., every 180 minutes),
    while preserving existing quiet-hours rule (skip 3:00–4:59 AM Eastern).
    """
    while True:
        try:
            # Get UTC time and convert to EST (fixed UTC-5 offset)
            now_utc = datetime.datetime.utcnow()
            now_est = now_utc + datetime.timedelta(hours=-5)
            est_hour = now_est.hour
            est_minute = now_est.minute

            # Determine if we should send an announcement at this time
            should_send = False

            if 3 <= est_hour < 5:
                logging.info("Skipping announcement: between 3AM and 5AM EST")
            elif est_hour in range(0, 3) or est_hour in range(5, 7):
                # During 12AM–3AM and 5AM–7AM EST, only send at :00
                if est_minute == 0:
                    should_send = True
            else:
               # All other hours: fire on every N-minute boundary (e.g., 180)
                total_minutes = est_hour * 60 + est_minute
                if total_minutes % frequency_minutes == 0:
                    should_send = True

            if should_send:
                message = msgs.newbie_announcement()
                if ENVIRONMENT == 'PROD':
                    helpers_telegram.send_message(SUPERGROUP_ID, message, NEWBIE_CHANNEL)
                    logging.info("Made newbie announcement")
                ## Kept turned off for dev to avoid sending messages all day in test bed 
                # elif ENVIRONMENT == 'DEV':
                #     helpers_telegram.send_message(SUPERGROUP_ID, message, NEWBIE_CHANNEL)
                #     logging.info("Made newbie announcement")

            # Sleep until the next frequency boundary (e.g. next multiple of N)
            now_utc = datetime.datetime.utcnow()
            now_est = now_utc + datetime.timedelta(hours=-5)
            total_now = now_est.hour * 60 + now_est.minute

            # Minutes remaining to the next boundary (e.g., next multiple of N)
            minutes_to_next = (frequency_minutes - (total_now % frequency_minutes)) % frequency_minutes
            
            if minutes_to_next == 0:
                # We're exactly on a boundary; schedule the *next* one.
                minutes_to_next = frequency_minutes

            # Convert to seconds and align to the next minute start
            seconds_until_next_tick = minutes_to_next * 60 - now_est.second
            time.sleep(max(1, seconds_until_next_tick))

        except Exception as e:
            logging.error(f"Error in announcement thread: {e}")
            time.sleep(60)


# Initialize the periodic announcement thread
def initialize_announcement_thread():
    logging.info("Starting periodic announcement thread...")
    thread = threading.Thread(target=start_periodic_announcement, daemon=True)
    thread.start()

# Initialize Global variables
def create_globals():
    global banned_data, newbies_mod_topics, dont_link_domains, ignore_domains, auto_poof_topics

    # Get banned topics
    with open('./mod_topics/moderated_topics.yml', 'r') as file:
        mod_topics_data = yaml.safe_load(file)
    banned_data = mod_topics_data.get('Banned_Topics', {})
    newbies_mod_topics = mod_topics_data.get('Newbies_Auto_Reply', {})
    auto_poof_topics = mod_topics_data.get('Auto_Poof_Topics', {})
    
    # Get dont link communities
    with open('./mod_topics/dont_link.yml', 'r') as file:
        domains = yaml.safe_load(file)
    dont_link_domains = domains.get('domain_urls', [])
    ignore_domains = domains.get('ignore_urls', [])
    
    logging.info("Setting global variables...")
    return banned_data, newbies_mod_topics, dont_link_domains, ignore_domains, auto_poof_topics

# Ensure thread is started and globals created on app import
# start_ai_roleplay_thread()
initialize_announcement_thread()
create_globals()
helpers_discord.start_discord_bridge()
helpers_invites.start_invite_rotation_thread()
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
    print(url)
    response = requests.post(url, json=payload)
    return response.json()

# Delete the webhook
@app.route('/deletewebhook', methods=['GET'])
def delete_webhook():
    url = f"{TELEGRAM_API_URL}/deleteWebhook"
    payload = {"url": f"{WEBHOOK_URL}"}
    print(url)
    response = requests.post(url, json=payload)
    return response.json()

# Check current webhook status
@app.route('/checkwebhook', methods=['GET'])
def check_webhook():
    url = f"{TELEGRAM_API_URL}/getWebhookInfo"
    print(url)
    response = requests.get(url)
    return response.json()

# Handle incoming updates
@app.route('/webhook', methods=['POST'])
def webhook():
    global banned_data, newbies_mod_topics, dont_link_domains, ignore_domains, auto_poof_topics
    
    # Log raw request data
    raw_data = request.data.decode('utf-8')
    logging.info(f"Raw request data: {raw_data}")
    
    try:
        update = request.get_json()
        if update is None:
            return jsonify({"error": "Invalid JSON format"}), 400
        
        ### AUTOMATED WELCOME MESSAGE FOR NEW MEMBER ###
        # Check for "new_chat_member" in the ChatMemberUpdated update
        if "chat_member" in update:
            chat_member_update = update["chat_member"]
            chat_id = chat_member_update.get("chat", {}).get("id")
            new_member = chat_member_update.get("new_chat_member", {}).get("user")
            new_status = chat_member_update.get("new_chat_member", {}).get("status")
            old_status = chat_member_update.get("old_chat_member", {}).get("status")
            logging.info(f"New member status: {new_status}, Old member status: {old_status}")
            # Check if the user has joined the group
            if new_status == "member" and old_status in ["left", "kicked"]:
                if str(chat_id) == SUPERGROUP_ID:
                    welcome_message = msgs.welcome_newbie(new_member)
                    helpers_telegram.send_message(chat_id, welcome_message)
                    return jsonify({"ok": True}), 200
            
        ### EXTRACT TG UPDATE IDs ###
        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id', None)
        message_thread_id = message.get("message_thread_id")
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
        if str(chat_id) != SUPERGROUP_ID:
            return jsonify({"ok": True}), 200  # Exit after handling the command for non-target groups
        
        ### ALL OTHER MESSAGES ###
        elif "message" in update:

            ### AUTO POOF MESSAGES WITH SPECIFIC TERMS ###
            normalized_text = unicodedata.normalize("NFKC", text)
            if str(message_thread_id) not in IGNORE_AUTOMOD_CHANNELS and username not in MOD_ACCOUNTS: 
                for _, data in auto_poof_topics.items():
                    banned_message = data.get('message')
                    banned_patterns = data.get('patterns')
                    for word in banned_patterns:
                        pattern = rf"\b{re.escape(word)}\b"
                        if re.search(pattern, normalized_text, re.IGNORECASE):
                            full_banned_message = msgs.banned_topic(word, banned_message, user=message.get('from', {}))
                            helpers_telegram.send_message(chat_id, full_banned_message)
                            logging.info(f"Auto-poofing message {message_id} in chat {chat_id} for pattern: {word}")
                            helpers_telegram.delete_message(chat_id, message_id)
                            return jsonify({"ok": True}), 200

            ### CHECK FOR BANNED TOPICS ###
            for _, data in banned_data.items():
                banned_message = data.get('message')
                banned_topics = data.get('substances')
                for tuple_topic in banned_topics:
                    for word in tuple_topic:
                        pattern = r'\b' + re.escape(word.lower()) + r'\b'
                        if re.search(pattern, text.lower()):
                            banned_topic_message = msgs.banned_topic(tuple_topic, banned_message)
                            helpers_telegram.send_message(chat_id, banned_topic_message, message_thread_id, reply_to_message_id=message_id)
                            return jsonify({"ok": True}), 200
                        
                ### REGEX PATTERNS PER BANNED TOPIC ###  
                banned_patterns = data.get('patterns', [])
                for rx in banned_patterns:
                    try:
                        if re.search(rx, text, flags=re.IGNORECASE | re.DOTALL):
                            banned_topic_message = msgs.banned_topic("Pattern match", banned_message)
                            helpers_telegram.send_message(chat_id, banned_topic_message, message_thread_id, reply_to_message_id=message_id)
                            return jsonify({"ok": True}), 200
                    except re.error as e:
                        logging.error(f"Invalid regex in banned pattern '{rx}': {e}")

            ### CHECK FOR SPECIFIC QUESTIONS IN NEWBIES CHANNEL ###
            if str(message_thread_id) == NEWBIE_CHANNEL and username not in MOD_ACCOUNTS:
                for topic, data in newbies_mod_topics.items():
                    if any(re.search(pattern, text) for pattern in data["patterns"]):
                        message = data["message"]
                        helpers_telegram.send_message(chat_id, message, message_thread_id, reply_to_message_id=message_id)
                        return jsonify({"ok": True}), 200


            ### WHEN DOC OR PHOTO POSTED IN TEST RESULTS CHANNEL 
            if ("document" in message or "photo" in message) and str(message_thread_id) == TEST_RESULTS_CHANNEL:
                # AUTO EXTRACT TEST RESULTS (always run)
                try:
                    test_results_summary = msgs.summarize_test_results(update, BOT_TOKEN)
                    helpers_telegram.send_message(chat_id, test_results_summary, message_thread_id)
                    logging.info("Test results extraction completed successfully")
                except Exception as e:
                    logging.error(f"Test results extraction failed: {e}")
                    helpers_telegram.send_message(
                        chat_id,
                        "🚫 Test results extraction failed. Please verify the file type and that all required details are present, then try again.",
                        message_thread_id,
                    )
                
                # DISCORD BRIDGE - TELEGRAM TO DISCORD (skip for bot messages)
                if str(chat_id) == SUPERGROUP_ID:
                    try:
                        file_id = None
                        filename = None
                        
                        if "photo" in message:
                            file_id = message["photo"][-1]["file_id"]
                            filename = "image.jpg"
                        elif "document" in message:
                            file_id = message["document"]["file_id"]
                            filename = message["document"].get("file_name", "document")
                        
                        if file_id:
                            file_response = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
                            file_data = file_response.json()
                            
                            if file_data.get("ok"):
                                file_path = file_data["result"]["file_path"]
                                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                                
                                display_name = username or user_firstname or "Anonymous"
                                caption = text if text else None
                                
                                helpers_discord.send_telegram_file_to_discord(display_name, file_url, filename, caption)
                                logging.info(f"Bridged Telegram→Discord: {display_name} ({filename})")
                                
                    except Exception as e:
                        logging.error(f"Failed to bridge Telegram file to Discord: {e}")
                
                return jsonify({"ok": True}), 200

            ### AUTO POOF LINKED COMMUNITIES ###
            # Flag t.me/ links in group test channel
            if "t.me/" in text and str(message_thread_id) == GROUP_TEST_CHANNEL and username not in MOD_ACCOUNTS: 
                logging.info(f"Detected t.me/ link in group test thread")
                reply_message = msgs.dont_link_group_test(user_id, user_firstname)
                helpers_telegram.send_message(chat_id, reply_message, message_thread_id, reply_to_message_id=message_id)
                helpers_telegram.delete_message(chat_id, message_id)
                return jsonify({"ok": True}), 200

            # If the text contains any ignored URL, skip moderation
            if any(ignore_url in text for ignore_url in ignore_domains):
                logging.info("Message contains an ignored URL. No moderation needed.")
                return jsonify({"ok": True}), 200
            
            # If the text contains any moderated domain, return a warning message
            for moderated_domain in dont_link_domains:
                if moderated_domain in text  and username not in MOD_ACCOUNTS:
                    logging.info(f"Detected moderated domain: {moderated_domain}")
                    reply_message = msgs.dont_link(user_id, user_firstname)
                    helpers_telegram.send_message(chat_id, reply_message, message_thread_id)
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
            chat_id, msgs.newbie_announcement(), message_thread_id, reply_to_message_id
        ),
        "/lastcall": lambda: helpers_telegram.send_message(
            chat_id, msgs.lastcall(update, BOT_TOKEN), message_thread_id, reply_to_message_id
        )
    }
    if command in command_dispatcher:
        return command_dispatcher[command]()
    else:
        try:
            return helpers_telegram.send_message(chat_id, msgs.unsupported(), message_thread_id, reply_to_message_id)
        except:
            return helpers_telegram.send_message(chat_id, msgs.unsupported())

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
#                 helpers_telegram.send_image(SUPERGROUP_ID, pic_path, message_thread_id=GENERAL_CHANNEL)
#                 for msg in exchange:
#                     helpers_telegram.send_message(SUPERGROUP_ID, msg, message_thread_id=GENERAL_CHANNEL)
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
#         helpers_telegram.send_image(SUPERGROUP_ID, 'murder_mystery_pics/tirzhelpbot.jpg', GENERAL_CHANNEL)
#         helpers_telegram.send_message(SUPERGROUP_ID, summary, GENERAL_CHANNEL)
#     else:
#         helpers_telegram.send_image(TEST_SUPERGROUP_ID, 'murder_mystery_pics/tirzhelpbot.jpg')
#         helpers_telegram.send_message(TEST_SUPERGROUP_ID, summary)
        
# def start_ai_roleplay_thread():
#     logging.info("Starting murder mystery roleplay...")
#     thread = threading.Thread(target=run_ai_conversation_loop, daemon=True)
#     thread.start()

if __name__ == "__main__":
    import argparse

    # Create argument parser
    parser = argparse.ArgumentParser(description="Manage Telegram bot webhooks.")
    parser.add_argument("--delete-webhook", action="store_true", help="Delete the current webhook.")
    parser.add_argument("--set-webhook", action="store_true", help="Set the webhook.")
    parser.add_argument("--check-webhook", action="store_true", help="Check the webhook status.")
    
    args = parser.parse_args()

    # Handle delete-webhook
    if args.delete_webhook:
        delete_response = delete_webhook()
        logging.info(f"Delete Webhook Response: {delete_response}")

    elif args.set_webhook:
        set_response = set_webhook()
        logging.info(f"Set Webhook Response: {set_response}")

    elif args.check_webhook:
        check_response = check_webhook()
        logging.info(f"Check Webhook Response: {check_response}")

    else:
        app.run(host="0.0.0.0", port=8443)
