import os
import sys
from uuid import uuid4
import numpy as np
import requests
import logging
import helpers_openai
import helpers_google

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)


def welcome_newbie(new_user):
    """
    Formats a welcome message for newbies.
    """
    wiki = "<a href='https://www.stairwaytogray.com/'>📖 Community Wiki</a>"
    mention = f"<a href='tg://user?id={new_user['id']}'>@{new_user['first_name']}</a> " if new_user!='' else new_user
    welcome_message = f"""{mention}Welcome to the Telegram community for r/tirzepatidehelp! 🎉 You've found your way to the end of the rabbit hole where you can ask all your questions about the gray peptide community, vendor sources, and more ✨🐰\n\nBefore jumping in, we've gathered answers to the most common newbie questions in our Wiki linked below💡\n\n{wiki}\n\nOnce you've read thru the <b>Who Are We?</b> and <b>Gray 101</b> guide, feel free to post any follow-up questions in the <i>Newbies</i> channel and further explore the *Guides* channel. We're here to help and happy to have you join us! 😊"""
    return welcome_message


def newbie_announcement():
    message = (
        "🚨 Here's your hourly Newbie Announcement 🚨\n\n"
        "Looking to learn about gray tirzepatide and don't know where to start? 🙋‍♂️🙋‍♀️\n\n"
        "<a href='https://www.stairwaytogray.com/posts/tirzepatide-101/'>Start with the wiki here 🌐</a> \n\n"
        "**Who are we?** We're a community of folks trying to get healthy by making the gray market safer and more accessible. 🫶💪\n\n"
        "Welcome to the gray space! 🤍 Let's get this research started..."
    )
    return message


def lastcall(update, BOT_TOKEN):
    # get chat member count
    chat_id = update['message']["chat"]["id"]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount"
    response = requests.get(url, params={'chat_id':chat_id})
    member_count = int(response.json().get("result")) - 1 # to account for Bot itself

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

        lastcall_message = f"""<b>Hello Researchers! 🧪🔬🌟</b>\n\nThis is your <b>FINAL reminder</b> and last call to decide if you'll be participating in this group test! 🚨 <b>The test will close at the end of today!</b>\n\nBy staying in this group chat after today, you’re committing to:  \n1️⃣ Paying your share of the testing costs within 24hrs of when the payment instructions are shared.  \n2️⃣ Receiving access to the test results!\n\n<b>Here’s the breakdown:</b>  \n- <b>Total testing cost:</b> ${test_cost}  \n- <b>Group size:</b> {member_count} members (not including TirzBot)  \n- <b>Estimated cost per member:</b> ${test_cost/split_members:.2f}\n\n{vial_donors_message}  \n\nIf you do not wish to participate, please select <b>"Leave Group"</b> from the group chat menu. <i>Archiving the chat won’t remove you from the group.</i>\n\nThank you for being a tester helping to make this community better for everyone! 🧪🔍"""
    except:
        lastcall_message = f"""💡<b>Use the following commands to calculate the test group split:</b>\n  •  <code>/lastcall cost=600</code>\n  •  <code>/lastcall cost=600 vialdonors=2</code> (to waive vial donors from paying test split)"""

    return lastcall_message


def safety():
    """
    Returns a Telegram message about harm reduction with a link to a section in a Google Doc.
    """
    links = [ 
        f"Check out the Testing section in the <a href='https://docs.google.com/document/d/1LHSXeIgIJFIcE3dsKEUUVyNyH2FT0Ku3ikWfdldg3Lk/edit?tab=t.0#heading=h.iet7p87aatw0'>Guides FAQ</a> for one of our best tools for safety in this community 🛡️🧪",
        f"Check out the aggregated stats we have on <a href='https://docs.google.com/spreadsheets/d/1S6OucgSjVmgWXWwGeBH31mxdtfkfH4u3omGQpLEWy-Y/edit?gid=1418853124#gid=1418853124'>Tirzepatide by Vendor</a> 📊",
        f"Check out the <a href='https://t.me/c/2462675990/2/71'>Basic Research Safety</a> summary 🦺",
        f"Check out the history and future <a href='https://www.nature.com/articles/s41392-022-00904-4'>applications of peptides</a> (or this <a href='https://chatgpt.com/share/67592350-1b00-800b-9c0c-b5604ea790ce'>ELI5 summarization by chatgpt</a>) 📝"
    ]
    message = f"Did someone say Safety? 👀\n\nIf you haven't already seen this one...\n\n{np.random.choice(links)}"
    return message

def banned_topic(banned_topic):
    link=""
    if 'DNP' in banned_topic:
        link = "https://pharmaceutical-journal.com/article/feature/dnp-the-dangerous-diet-pill-pharmacists-should-know-about"

    message = f"""⚠️ Safety Warning ⚠️ The following topic is not allowed for discussion for newcomer safety: \n\n{banned_topic}\n\n{link}"""

    return message


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
                "🟢" if stats['mass_diff_percent'] <= 5 else # more stringent USP standard
                "🟡" if stats['mass_diff_percent'] <= 10 else # USP <905> & USP <797>
                "🔴" if stats['mass_diff_percent'] > 10 else
                "⚪"
            )
            icon_status_purity = (
                "🟢" if stats['std_purity'] <= 2 else # from API tirz COA for FDA registered manufacturer 
                "🟡" if stats['std_purity'] <= 4 else # arbitrary doubled
                "🔴" if stats['std_purity'] > 4 else 
                "⚪"
            )
            message_text += (
                f"🔹 <b>Expected Mass: {expected_mass} mg</b>\n"
                f"   • Avg Tested Mass: {stats['average_mass']:.2f} mg\n"
                f"   • Avg Tested Purity: {stats['average_purity']:.2f}%\n"
                f"   • # Vials Tested: {stats['test_count']}\n"
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


def unsupported():
    markdown = r"""<code>stop poking me. seriously though. this command doesn't do anything. now clean up your mess.</code>"""
    return markdown