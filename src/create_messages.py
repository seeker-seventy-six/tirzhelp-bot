import os
import sys
from uuid import uuid4
import numpy as np
import requests
import logging

sys.path.append('./src')
from src import helpers_openai
from src import helpers_google

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)


def welcome_newbie(new_user):
    """
    Formats a welcome message for newbies.
    """
    wiki = "<a href='https://www.stairwaytogray.com/'>📖 Community Wiki</a>"
    guides = "<a href='https://t.me/c/2410577414/3/157'>📚 Guides Channel</a>"
    mention = f"<a href='tg://user?id={new_user['id']}'>@{new_user['first_name']}</a> " if new_user!='' else new_user
    welcome_message = f"""{mention}Welcome to the Telegram community for r/tirzepatidehelp :: Stairway to Gray! 🎉 You've found your way to the end of the rabbit hole where you can ask all your questions about the gray peptide community, vendor sources, and more ✨🐰\n\nBefore jumping in, we've gathered answers to the most common newbie questions in our Wiki and Guides channel linked below💡\n\n{wiki}\n{guides}\n\nOnce you've read thru the <b>Who Are We?</b> and <b>Gray 101</b> guide, feel free to post any follow-up questions in the <i>Newbies</i> channel and further explore the <i>Guides</i> channel. We're here to help and happy to have you join us! 😊"""
    return welcome_message


def newbie_announcement():
    message = (
        "🚨 Here's your hourly Newbie Announcement 🚨\n\n"
        "Looking to learn about gray tirzepatide and don't know where to start? 🙋‍♂️🙋‍♀️\n\n"
        "<a href='https://www.stairwaytogray.com/posts/tirzepatide-101/'>Start with the wiki here 🌐</a> \n\n"
        "<b>Who are we?</b> We're a community of folks trying to get healthy by making the peptide gray market safer and more accessible. 🫶💪\n\n"
        "Welcome to the gray space! Let's get this research started..."
    )
    return message
    

def lastcall(update, BOT_TOKEN):
    # Get chat member count
    chat_id = update['message']["chat"]["id"]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount"
    response = requests.get(url, params={'chat_id': chat_id})
    member_count = int(response.json().get("result")) - 1  # To account for Bot itself

    # Get the full command text after '/lastcall'
    command_text = update['message']['text'][len('/lastcall '):].strip()

    # Parse arguments
    arguments = {}
    for pair in command_text.split(' '):
        if '=' in pair:  # Only process valid key=value pairs
            key, value = map(str.strip, pair.split('=', 1))  # Allow for `key=value` with extra spaces
            arguments[key] = value

    # Validate and extract parameters
    try:
        test_cost = float(arguments['cost'])
        vial_donors = int(arguments['vialdonors'])
        vdvalue = float(arguments.get('vdvalue', 0))
        split_members = member_count - vial_donors

        if split_members <= 0:
            raise ValueError("Split members must be greater than 0")

        # Calculate the splits
        non_vial_split = (test_cost + (vial_donors * vdvalue)) / member_count
        vial_donor_split = non_vial_split - vdvalue

        # Construct vial donors message
        vial_donors_message = (
            f"\n\n✨ <b>NOTE:</b> Each vial donor is contributing an effective value of ${vdvalue:.2f} "
            f"towards the group effort by providing a vial and paying for their shipping, which has been accounted for in the calculations. Their adjusted share is lower." 
            if vial_donors else ""
        )

        # Construct final message
        lastcall_message = (
            f"""<b>⚠️ FINAL CALL, Researchers! ⚠️</b>\n\nThis is now the time to confirm your participation in the group test! 🚨 The test closes in <b>24 hours</b>.\n\nRemaining in this group means you'll: \n1️⃣ Pay your share within 48hrs of posted payment instructions. \n2️⃣ Receive access to the test results!\n\n<b>Cost Breakdown:</b>\n- <b>Total cost:</b> ${test_cost} \n- <b>Cost per member:</b> \n  ${non_vial_split:.2f} (non-vial) \n  ${vial_donor_split:.2f} (vial donor){vial_donors_message}\n\nIF YOU WISH TO PARTICIPATE, PLEASE REACT TO THIS MESSAGE ✅. If we don't hear from you, we'll assume you no longer wish to participate and you will be removed once the group test closes💨\n\nThanks for helping improve the peptide testing community! 🧪🔍"""
        )

    except:
        lastcall_message = f"""💡<b>Use the following command to calculate the test group split:</b>\n\n <code>/lastcall cost=600 vialdonors=2 vdvalue=20</code> \n\n(to account for vial donors' effective contributions)"""

    return lastcall_message

def safety():
    """
    Returns a Telegram message about harm reduction with a link to a section in a Google Doc.
    """
    links = [ 
        f"Check out the Testing section in the <a href='https://docs.google.com/document/d/1LHSXeIgIJFIcE3dsKEUUVyNyH2FT0Ku3ikWfdldg3Lk/edit?tab=t.0#heading=h.iet7p87aatw0'>Guides FAQ</a> for one of our best tools for safety in this community 🛡️🧪",
        f"Check out the aggregated stats we have on <a href='https://docs.google.com/spreadsheets/d/1S6OucgSjVmgWXWwGeBH31mxdtfkfH4u3omGQpLEWy-Y/edit?gid=1418853124#gid=1418853124'>Tirzepatide by Vendor</a> 📊",
        f"Check out the history and future <a href='https://www.nature.com/articles/s41392-022-00904-4'>applications of peptides</a> 📝",
        "Always check your reconstituted peptide's pH level before injecting! 🧪📈 Tirzepatide should fall in the 6-9 pH range. (For subQ injections, 4-9 pH is generally considered 'safe' for injection comfort.) Find any pH 0-14 strips on Amazon.",
    ]
    message = f"Did someone say Safety? 👀\n\nIf you haven't already seen this one...\n\n{np.random.choice(links)}"
    return message

def banned_topic(banned_topic, header_msg, topic_msg=""):
    if 'DNP' in banned_topic:
        topic_msg = "\nhttps://pharmaceutical-journal.com/article/feature/dnp-the-dangerous-diet-pill-pharmacists-should-know-about"
    elif 'Botox' in banned_topic:
        topic_msg = "\nCurrently, there are no known labs in the community who can test Botox to verify the potency of active ingredient. Given that a 100-unit vial of Botox contains only 5-20 nanograms of the active toxin, even slight errors in dosage can significantly increase the risk of lethal toxicity. For safety reasons, we strongly advise against DIY Botox, especially when sourced from unregulated, untested vendors.\n<a href='https://pmc.ncbi.nlm.nih.gov/articles/PMC2856357/'>source</a>"

    message = f"""{header_msg}\n\n{banned_topic}\n{topic_msg}"""

    return message


def dont_link(user_id, user_name):
    message = (
        f"<a href='tg://user?id={user_id}'>@{user_name}</a> 💨🚫 "
        "We're auto-poofing this direct link as most communities have requested invites be shared only through approved links or not to be directly linked. \n\n"
        "We don't like gatekeeping info either, but we also want to be good neighbors and respect their moderation wishes. Please DM any invite links instead. \n\n"
        "You can also check the <a href='https://docs.google.com/document/d/1CvAu42nH0i-VFPN9cLInSkjj7D8F0SBq7FIyqDjhF7M/edit?tab=t.lgryvp324lcd'>Printable Guides: External Resources</a> for the latest approved community invite method if provided. Thank you! 🙏"
    )
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
                + [sample.test_link]
                + [sample.test_key]
                + [sample.test_task]
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
        return "😳🚧 Oops! We cannot parse this test result. This test type may not be supported yet, but we're working on supporting more test types soon!"


def unsupported():
    markdown = r"""<code>stop poking me. this command doesn't do anything.</code>"""
    return markdown