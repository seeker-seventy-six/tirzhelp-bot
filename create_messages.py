import os
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
    guides_toc = "<a href='https://t.me/c/2462675990/2/36295'>📖Guides Channel Table of Contents</a>"
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
    try:
        test_cost = float(arguments['cost'])
        vial_donors = int(arguments.get('vialdonors',0))
        split_members = member_count - vial_donors
        
        # construct message
        vial_donors_message = f"✨ <b>NOTE:</b> The group has decided to waive the test payment for our {vial_donors} vial donors, so their shares have already been accounted for in this calculation." if vial_donors else ""

        lastcall_message = f"""<b>Hello Researchers! 🧪🔬🌟</b>\n\nThis is your <b>FINAL reminder</b> and last call to decide if you'll be participating in this group test! 🚨 <b>The test will close at the end of today!</b>\n\nBy staying in this group chat after today, you’re committing to:  \n1️⃣ Paying your share of the testing costs within 24hrs of when the payment instructions are shared.  \n2️⃣ Receiving access to the test results!\n\n<b>Here’s the breakdown:</b>  \n- <b>Total testing cost:</b> ${test_cost}  \n- <b>Group size:</b> {member_count} members (including you!)  \n- <b>Estimated cost per member:</b> ${test_cost/split_members:.2f}\n\n{vial_donors_message}  \n\nIf you do not wish to participate, please select <b>"Leave Group"</b> from the group chat menu. <i>Archiving the chat won’t remove you from the group.</i>\n\nThank you for being a tester helping to make this community better for everyone! 🧪🔍"""
    except:
        lastcall_message = f"""💡<b>Use the following commands to calculate the test group split:</b>\n  •  <code>/lastcall cost=600</code>\n  •  <code>/lastcall cost=600 vialdonors=2</code> (to waive vial donors from paying test split)"""
        
    return lastcall_message


def summarize_test_results(update, BOT_TOKEN):
    message = update["message"]
    text = message.get("text", "")

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
    extracted_test_data = helpers_openai.extract_data_with_openai(local_path, text)
    logging.info(f"Extracted data returned: {extracted_test_data}")

    if extracted_test_data:
        # Append data to Google Sheets for each sample tested. One Test Result image may have more than one sample
        for sample in extracted_test_data:
            data_row = (
                [sample.vendor]
                + [sample.peptide]
                + [sample.test_date]
                + [sample.batch]
                + [sample.expected_mass_mg]
                + [sample.mass_mg]
                + [sample.purity_percent]
                + [sample.tfa_present]
                + [sample.test_lab]
                + [local_path.split('/')[-1]]
            )
            helpers_google.append_to_sheet(data_row)

        # Calculate statistics
        grouped_stats = helpers_google.calculate_statistics(sample.vendor, sample.peptide)

        # Initialize the message text
        message_text = f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()} Analysis for the last 3 months:</b>\n\n"

        raw_data_url =  "<a href='https://docs.google.com/spreadsheets/d/1S6OucgSjVmgWXWwGeBH31mxdtfkfH4u3omGQpLEWy-Y/edit?usp=sharing'>you can find the raw data here</a>"

        # Iterate through each group and append stats to the message
        for expected_mass, stats in grouped_stats.items():
            icon_status_mass = (
                "🟢" if stats['mass_diff_percent'] <= 5 else 
                "🟡" if stats['mass_diff_percent'] <= 10 else 
                "🔴" if stats['mass_diff_percent'] > 10 else
                "⚪"
            )
            icon_status_purity = (
                "🟢" if stats['std_purity'] <= 2 else 
                "🟡" if stats['std_purity'] <= 4 else 
                "🔴" if stats['std_purity'] > 4 else 
                "⚪"
            )
            message_text += (
                f"🔹 <b>Expected Mass: {expected_mass} mg</b>\n"
                f"   • Avg Tested Mass: {stats['average_mass']:.2f} mg\n"
                f"   • Avg Tested Purity: {stats['average_purity']:.2f}%\n"
                f"   • Typical Deviation Tested Mass (Std Dev): +/-{stats['std_mass']:.1f} mg\n"
                f"   {icon_status_mass} <b>+/-{stats['mass_diff_percent']:.1f}% : % Std Dev of Mass from Expected mg</b>\n"
                f"   {icon_status_purity} <b>+/-{stats['std_purity']:.1f}% : % Std Dev of Purity from 100%</b>\n\n"
            )

        # Clean up
        os.remove(local_path)
        logging.info(f"Message: {message_text}")
        return message_text + raw_data_url
    
    else:
        return "😳🚧 This test type isn't supported yet, but we're working on adding more test types to parse as soon as possible!"


def summarize():
    markdown = """<code> 
  _  _    ___  _  _         
 | || |  / _ \| || |        
 | || |_| | | | || |_       
 |__   _| | | |__   _|      
    | | | |_| |  | |        
    |_|  \___/   |_|        
 __          _______ _____  
 \ \        / |_   _|  __ \ 
  \ \  /\  / /  | | | |__) |
   \ \/  \/ /   | | |  ___/ 
    \  /\  /   _| |_| |     
     \/  \/   |_____|_|     </code>"""
    return markdown