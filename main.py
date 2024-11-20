import telebot
import os

# Load BOT_TOKEN and GROUP_CHAT_ID from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# Validate environment variables
if not BOT_TOKEN or not GROUP_CHAT_ID:
    raise ValueError("Please set the BOT_TOKEN and GROUP_CHAT_ID environment variables.")


# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Define the /newbie command handler
@bot.message_handler(commands=['newbie'])
def welcome_newbie():
    """
    Sends a welcome message to the group when the /newbie command is used.
    """
    # Format your message
    guides_toc = "<a href='https://t.me/c/2462675990/2/75'>📖Guides Channel Table of Contents</a>"; 
    newbie_faq = "<a href='https://docs.google.com/document/d/1LHSXeIgIJFIcE3dsKEUUVyNyH2FT0Ku3ikWfdldg3Lk/edit?usp=sharing'>❓Newbie FAQ</a>";
    greeting_message = "Welcome to the Telegram community for r/tirzepatidehelp! 🎉 You've found your way to the end of the rabbit hole where you can ask all your questions about vendor sources and more ✨🐰\n\nBefore jumping in, we’ve gathered answers to the most common newbie questions in the Guides channel💡 Once you’ve checked it out, feel free to post any follow-up questions in the appropriate channel. We're here to help and excited to have you join the conversation! 😊\n"
    welcome_message = greeting_message + guides_toc + newbie_faq

    # Send the message with additional parameters
    bot.send_message(
        GROUP_CHAT_ID,
        welcome_message,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

# Polling to keep the bot running
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()