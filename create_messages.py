from flask import jsonify
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import requests
import logging
import helpers_openai
import helpers_google

# Setup basic logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def welcome_newbie(new_user):
    """
    Formats a welcome message for newbies.
    """
    guides_toc = "<a href='https://t.me/c/2462675990/2/75'>📖Guides Channel Table of Contents</a>"
    newbie_faq = "<a href='https://docs.google.com/document/d/1LHSXeIgIJFIcE3dsKEUUVyNyH2FT0Ku3ikWfdldg3Lk/edit?usp=sharing'>❓Newbie FAQ</a>"
    mention = f"<a href='tg://user?id={new_user['id']}'>@{new_user['first_name']}</a> " if new_user!='' else new_user
    greeting_message = f"""{mention}Welcome to the Telegram community for r/tirzepatidehelp! 🎉 You've found your way to the end of the rabbit hole where you can ask all your questions about vendor sources and more ✨🐰\n\nBefore jumping in, we’ve gathered answers to the most common newbie questions in the Guides channel linked below💡 Once you’ve checked it out, feel free to post any follow-up questions in the appropriate channel. We're here to help and excited to have you join the conversation! 😊"""
    
    welcome_message = f"""{greeting_message}\n\n{guides_toc}\n{newbie_faq}"""

    return welcome_message


def lastcall(update, BOT_TOKEN):
    # get chat member count
    chat_id = update['message']["chat"]["id"]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount"
    response = requests.get(url, params={'chat_id':chat_id})
    member_count = int(response.json().get("result"))

    # Get the full command text after '/lastcall'
    command_text = update['message']['text'][len('/lastcall '):].strip()
    # Parse arguments (basic example)
    arguments = {}
    if '=' in command_text:
        pairs = command_text.split(' ')
        for pair in pairs:
            key, value = pair.split('=')
            arguments[key] = value
    # Access specific arguments
    test_cost = float(arguments.get('cost',0))
    vial_donors = int(arguments.get('vialdonors',0))
    split_members = member_count - vial_donors
    
    # construct message
    vial_donors_message = f"✨ <b>NOTE:</b> The group has decided to waive the test payment for our {vial_donors} vial donors, so their shares have already been accounted for in this calculation." if vial_donors else ""

    lastcall_message = f"""<b>Hello Researchers! 🧪🔬🌟</b>\n\nThis is your <b>FINAL reminder</b> and last call to decide if you'll be participating in this group test! 🚨 <b>The test will close at the end of today!</b>\n\nBy staying in this group chat after today, you’re committing to:  \n1️⃣ Paying your share of the testing costs within 24hrs of when the payment instructions are shared.  \n2️⃣ Receiving access to the test results!\n\n<b>Here’s the breakdown:</b>  \n- <b>Total testing cost:</b> ${test_cost}  \n- <b>Group size:</b> {member_count} members (including you!)  \n- <b>Estimated cost per member:</b> ${test_cost/split_members:.2f}\n\n{vial_donors_message}  \n\nIf you do not wish to participate, please select <b>"Leave Group"</b> from the group chat menu. Just a heads-up: <i>archiving the chat won’t remove you from the group.</i>\n\nThank you for being part of the testers who are making this community better for everyone! 🧪🔍"""
    
    return lastcall_message


def summarize_test_results(update, BOT_TOKEN):
    message = update["message"]

    # Handle documents or photos
    if "document" in message:
        file_id = message["document"]["file_id"]
    elif "photo" in message:
        file_id = message["photo"][-1]["file_id"]
    else:
        raise ValueError("No document or photo found in the message.")

    # Get file info
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
    file_info = requests.get(url, params={"file_id": file_id}).json()
    file_path = file_info["result"]["file_path"]

    # Download the file
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    downloaded_file = requests.get(file_url).content
    local_path = f"./temp{uuid4()}/{os.path.basename(file_path)}"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(downloaded_file)

    # Process the file using OpenAI
    extracted_data = helpers_openai.extract_data_with_openai(local_path)

    # Append data to Google Sheets
    data_row = (
          [extracted_data.vendor]
        + [extracted_data.peptide]
        + [extracted_data.test_date]
        + [extracted_data.batch]
        + [extracted_data.expected_mass_mg]
        + [extracted_data.mass_mg]
        + [extracted_data.purity_percent]
        + [extracted_data.test_lab]
    )

    helpers_google.append_to_sheet(data_row)

    # Calculate statistics
    grouped_stats = helpers_google.calculate_statistics(extracted_data.vendor, extracted_data.peptide)

    # Initialize the message text
    message_text = f"📊 <b>{extracted_data.vendor.upper()} {extracted_data.peptide.upper()} Analysis for the last 3 months:</b>\n\n"

    # Iterate through each group and append stats to the message
    for expected_mass, stats in grouped_stats.items():
        message_text += (
            f"🔹 <b>Expected Mass: {expected_mass} mg</b>\n"
            f"   • Avg Tested Mass: {stats['average_mass']:.2f} mg\n"
            f"   • Avg Tested Purity: {stats['average_purity']:.2f}%\n"
            f"   • Std Dev Mass: {stats['std_mass']:.2f} mg\n"
            f"   • Std Dev Purity: {stats['std_purity']:.2f}%\n\n"
        )

    # Clean up
    os.remove(local_path)

    return message_text


def summarize(update, BOT_TOKEN, OPENAI_TOKEN):
    # try:
    #     # get telegram ids
    #     chat_id = update['message']['chat']['id']
    #     message_thread_id = update['message']['message_thread_id']
    
    #     # Get the current time in UTC and calculate the time 24 hours ago
    #     now = datetime.now(timezone.utc)
    #     one_day_ago = now - timedelta(hours=24)

    #     # Fetch messages from the chat in the last 24 hours
    #     url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    #     response = requests.get(url).json()
    #     logging.debug(f"response: {response}")

    #     # Filter messages from the current chat and within the last 24 hours
    #     messages = [
    #         update["message"]["text"]
    #         for update in response.get("result", [])
    #         if update.get("message", {}).get("message_thread_id", {}) == message_thread_id
    #         and datetime.fromtimestamp(update["message"]["date"], tz=timezone.utc) >= one_day_ago
    #     ]

    #     # If no messages found, respond accordingly
    #     if not messages:
    #         return jsonify({"error": "No messages found in the last 24 hours to summarize."}), 500

    #     # Join messages for summarization
    #     combined_text = "\n".join(messages)

    #     logging.debug(f"Messages in past 24 hours: {combined_text}")

        # # Summarize using Bedrock LLaMA2
        # client = OpenAI(
        #     organization='org-ukPKUNI1vD72DYjb83IEpRSq',
        #     project='proj_kXDhtH3besJxGcqXaqV20Yk6',
        # )
        # summary_response = client.ChatCompletion.create(
        #     model="llama2",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful summarization assistant."},
        #         {"role": "user", "content": combined_text},
        #     ],
        # )
        # summary = summary_response["choices"][0]["message"]["content"]

        # # Send the summary back to the user
        # update.message.reply_text(summary)
    try:
        return "WIP"

    except Exception as e:
        logging.error(f"Error in summarize command: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500