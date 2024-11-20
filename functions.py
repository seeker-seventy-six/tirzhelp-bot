
def welcome_newbie():
    """
    Formats a welcome message for newbies.
    """
    guides_toc = "<a href='https://t.me/c/2462675990/2/75'>📖Guides Channel Table of Contents</a>"
    newbie_faq = "<a href='https://docs.google.com/document/d/1LHSXeIgIJFIcE3dsKEUUVyNyH2FT0Ku3ikWfdldg3Lk/edit?usp=sharing'>❓Newbie FAQ</a>"
    greeting_message = """
    Welcome to the Telegram community for r/tirzepatidehelp! 🎉 You've found your way to the end of the rabbit hole where you can ask all your questions about vendor sources and more ✨🐰\n\nBefore jumping in, we’ve gathered answers to the most common newbie questions in the Guides channel linked below💡 Once you’ve checked it out, feel free to post any follow-up questions in the appropriate channel. We're here to help and excited to have you join the conversation! 😊"""
    
    welcome_message = "\n".join([greeting_message + guides_toc + newbie_faq])

    return welcome_message


def summarize_channel():
    return "🛠️WIP🛠️"

