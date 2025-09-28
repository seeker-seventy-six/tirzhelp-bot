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
    wiki = "<a href='https://www.stairwaytogray.com/'>📖 Community Intro</a>"
    guides = "<a href='https://t.me/c/2410577414/3/51643'>📚 Rules & Guides Channel</a>"
    mention = f"<a href='tg://user?id={new_user['id']}'>@{new_user.get('username', new_user['first_name'])}</a> " if new_user!='' else new_user
    welcome_message = (
        f"{mention} Welcome to the Telegram community for Stairway to Gray! 🎉 \n\nYou've found your way to the end of the rabbit hole where you can ask all your questions about the gray peptide community, vendor sources, and more ✨🐰\n\n"
        f"Before jumping in, we've gathered answers to the most common newbie questions in our <b>Gray 101</b> guide and <b>Rules & Guides channel</b> linked below:\n\n{wiki}\n{guides}\n\n"
        f"Once you've read thru these guides, feel free to post follow-up questions in the <i>Newbies</i> channel and further explore the <i>Rules & Guides</i> channel. We're here to help and happy to have you join us! 😊"
    )
    return welcome_message


def newbie_announcement():
    safety_tip = np.random.choice([
        "Never trust unsolicited DMs — scammers often impersonate vendor reps. Always verify rep contacts through the vendor spreadsheet or vendor's community.",
        "Check your reconstituted peptide's pH level before injecting! 🧪📈 GLP-1s should fall in the 6-9 pH range. (For subQ injections, 4-9 pH is generally considered 'safe' for injection comfort.) Find pH strips on Amazon.",
        "Check out the aggregated stats we have on <a href='https://docs.google.com/spreadsheets/d/1IbMh3BNqkQP-0ZyI51Dyz8K-msSHRiY_kT0Ue-Uv8qQ/edit?gid=1418853124#gid=1418853124'>Tirzepatide by Vendor</a> 📊",
        "We don't recommend single vial vendors in this community because they cannot be tested and therefore lack the same level of accountability for quality control as kits. If you choose to use a single vial vendor, please do so at your own risk and thoroughly research.",
        "Vendor COAs are 🧻 - they can be biased due to cherry-picking. Use them only to verify what the vendor *claims* to be selling. To mitigate risk, third-party (3P) test your actual order!",
        "We don't recommend individual-ran group buys for first-time buyers because of the increased risk of scams and typically a lack of leverage to make buyers whole in the event of an issue. If you choose to go the group buy route, please do so at your own risk and thoroughly research."
    ])
    message = (
        "🚨 New here? Start here! 🚨\n\n"
        "Curious about gray market GLP-1s but not sure where to begin? We've got you covered 🙌\n\n"
        "1) Start with the Rules & Guides channel:\n<a href='https://t.me/c/2410577414/3/51643'>Rules & Guides 📚</a>\n\n"
        "2) Read our intro guide:\n<a href='https://www.stairwaytogray.com/posts/tirzepatide-101/'>Gray 101 🌐</a>\n\n"
        "<b>Who are we?</b> We're a community focused on making the peptide gray market safer to navigate and provide community support and connection. 🧪🫂💬\n\n"
        f"⚠️ <b>Safety Tip:</b> {safety_tip}"
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
        f"Check out the aggregated stats we have on <a href='https://docs.google.com/spreadsheets/d/1IbMh3BNqkQP-0ZyI51Dyz8K-msSHRiY_kT0Ue-Uv8qQ/edit?gid=1418853124#gid=1418853124'>Tirzepatide by Vendor</a> 📊",
        f"Check out the history and future <a href='https://www.nature.com/articles/s41392-022-00904-4'>applications of peptides</a> 📝",
        "Always check your reconstituted peptide's pH level before injecting! 🧪📈 Tirzepatide should fall in the 6-9 pH range. (For subQ injections, 4-9 pH is generally considered 'safe' for injection comfort.) Find any pH 0-14 strips on Amazon.",
    ]
    message = f"Did someone say Safety? 👀\n\nIf you haven't already seen this one...\n\n{np.random.choice(links)}"
    return message

def banned_topic(banned_topic, header_msg, topic_msg="", user=None):
    if user:
        mention = f"<a href='tg://user?id={user['id']}'>@{user.get('username', user['first_name'])}</a> "
    else:
        mention = ""

    if 'DNP' in banned_topic:
        topic_msg = "\nThis is a highly dangerous mitochondrial decoupler.\nhttps://pharmaceutical-journal.com/article/feature/dnp-the-dangerous-diet-pill-pharmacists-should-know-about"
    elif 'Botox' in banned_topic:
        topic_msg = "\nCurrently, there are no known labs in the community who can test Botox to verify the potency of active ingredient. Given that a 100-unit vial of Botox contains only 5-20 nanograms of the active toxin, even slight errors in dosage can significantly increase the risk of lethal toxicity. For safety reasons, we strongly advise against DIY Botox, especially when sourced from unregulated, untested vendors.\n<a href='https://pmc.ncbi.nlm.nih.gov/articles/PMC2856357/'>source</a>"
    elif 'BAM15' in banned_topic:
        topic_msg = "\nThis is a dangerous mitochondrial decoupler."
    
    message = f"""{mention}{header_msg}\n\nauto-moderated term: {banned_topic}\n{topic_msg}""".strip()
    return message

def dont_link(user_id, user_name):
    message = (
        f"<a href='tg://user?id={user_id}'>@{user_name}</a> 💨🚫 "
        "We're auto-poofing this direct link as most communities have requested invites be shared only through approved links or not to be directly linked.\n\n"
        "If this was an order form, we also auto-poof these for newbie safety. Newbies should ask around here for experiences with the vendor.\n\n"
        "Please DM these kinds of links instead, but be vigilant as a newbie receiving DMs.\n\n"
        "You can check the <a href='https://docs.google.com/document/d/1CvAu42nH0i-VFPN9cLInSkjj7D8F0SBq7FIyqDjhF7M/edit?tab=t.lgryvp324lcd'>Printable Guides: External Resources</a> for the latest approved community invite method if they've provided one, the <a href='https://t.me/c/2410577414/37/389306'>Supply Vendors Spreasheet</a>, or the <a href='https://t.me/c/2410577414/3/51651'>Vendor Spreadhseet</a>. Thank you! 🙏"
    )
    return message

def dont_link_group_test(user_id, user_name):
    message = (
    f"<a href='tg://user?id={user_id}'>@{user_name}</a> 💨🚫 Ope! "
    "STG has moved group testing support to the new testing server STGTS on Discord. You can find that linked below, along with mods and group support to help you in your testing journey!\n\n"
    "https://discord.gg/7m2XhYu4ug \n\n"
    "While the most important thing is that members test what they buy for safety, please be aware that TG private chat testing groups will no longer have mod support if something goes wrong. "
    "Please join TG organized groups at your own risk. 🙏\n\n"
    "To post your group test here, either copy the discord # looking-for-group-test THREAD link <a href='https://discord.com/channels/1351746139325595748/1359204768983289856/1361058059895570503'>(learn how here)</a>"
    ", or post the discord channel name of your OPEN group test so folks can join from the <a href='https://discord.com/channels/1351746139325595748/1352074864906735687'>#start-join-leave-test-groups</a> channel"
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
                + [sample.endotoxin]
                + [sample.test_lab]
                + [local_path.split('/')[-1]]
                + [sample.test_link]
                + [sample.test_key]
                + [sample.test_task]
            )
            helpers_google.append_to_sheet(data_row)

        raw_data_url =  "<a href='https://docs.google.com/spreadsheets/d/1IbMh3BNqkQP-0ZyI51Dyz8K-msSHRiY_kT0Ue-Uv8qQ'>🌐 You can find the raw data here</a>"
        if sample.mass_mg:
            grouped_stats = helpers_google.calculate_statistics(sample.vendor, sample.peptide)
            logging.info(f"Grouped stats: {grouped_stats}")
            # Initialize the message text
            message_text = f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()} Analysis for the last 6 months:</b>\n\n"

            # Iterate through each group and append stats to the message
            for expected_mass, stats in grouped_stats.items():
                icon_status_mass = (
                    "🟢" if stats['mass_diff_percent'] <= 10 else # more stringent USP standard
                    "🟡" if stats['mass_diff_percent'] <= 15 else # USP <905> & USP <797>
                    "🔴" if stats['mass_diff_percent'] > 15 else
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
                    f"   • Mass Variation between Vials (Std Dev): ±{stats['std_mass']:.1f} mg\n"
                    f"   {icon_status_mass} <b>±{stats['mass_diff_percent']:.1f}% Mass Variation from Expected Mass</b>\n"
                    f"   {icon_status_purity} <b>±{stats['std_purity']:.1f}% Purity Variation</b>\n\n"
                )

            # Clean up
            os.remove(local_path)
            logging.info(f"Message: {message_text + raw_data_url}")
            return message_text + raw_data_url
        
        elif sample.endotoxin:
            message_text = (
                f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()}</b>\n\n"
                f"🔹 <b>Endotoxin Level:</b> {sample.endotoxin}\n\n"
                f"<i>Note:</i> Endotoxin is measured in EU (Endotoxin Units). For tirzepatide, <b>&lt;10 EU/mg</b> is the recommended threshold from FDA-registered API standards.\n"
                f"• Janoshik reports EU per vial → divide by Y mg to get EU/mg\n"
                f"• TrustPointe reports EU/mL → divide by (Y mg ÷ 2mL) to get EU/mg\n"
                f"<a href='https://www.stairwaytogray.com/posts/testing/testing-101/#endotoxin'>More details in the Testing 101 Guide 🔬</a>\n\n"
            )
            os.remove(local_path)
            logging.info(f"Message: {message_text + raw_data_url}")
            return message_text + raw_data_url
        
        else:
            message_text = (
                f"📊 <b>{sample.vendor.upper()} {sample.peptide.upper()}</b>\n\n"
                f"🔹<a href='https://www.stairwaytogray.com/posts/testing/testing-101/#how-do-i-read-my-test-results'>How Do I Read My Test Results? Check out the Testing 101 Guide 🔬</a>\n\n"
            )
            os.remove(local_path)
            logging.info(f"Message: {message_text + raw_data_url}")
            return message_text + raw_data_url
    
    else:
        return "😳🚧 Oops! We cannot parse this test result. This test type may not be supported yet, but we're working on supporting more test types soon!"


def unsupported():
    markdown = r"""<code>tehehe stop poking me. this command doesn't do anything.</code>"""
    return markdown