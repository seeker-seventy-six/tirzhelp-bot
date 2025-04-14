# 🤖 TirzHelpBot
*A Telegram Bot API Heroku App for Stairway to Gray (aka r/TirzepatideHelp)*

This is a Flask-based application that integrates with the Telegram Bot API. It allows you to interact with Telegram supergroups and handle commands from users. The bot is set up with a webhook to process incoming updates and respond accordingly.

Once the bot is deployed to Heroku and added as a member to a Telegram supergroup or group chat, it can be used for the following features.

## Features

- **Webhook Handling**: Listens to incoming updates and processes commands like `/newbie`, `/lastcall`, and `/safety`.
- **Automatic Welcome**: Welcomes new users when they join specific supergroups.
- **Banned Topic Filtering**: Filters messages for banned topics and alerts the user if a topic is found. It can also auto-delete messages for certain terms organized by yaml files.
- **Automated Messages**: Can automatically respond to certain terms or regex patterns with predefined messages for certain terms organized by yaml files.
- **Test Results Extraction**: Extract any document (pdf) or image uploaded to Test Results channel and upload the extracted data to a Google Spreadsheet automatically.

## Environment Setup

Before deploying, create a `.env-dev` and `.env-prod` file with the following environment variables for each bot environment. If developing on the existing bot, these can be found on the Heroku Dashboard > [Application Name] > Settings > Config Vars:

```
BOT_TOKEN=your-telegram-bot-token
WEBHOOK_URL=https://your-heroku-app-url/webhook
ENVIRONMENT=[PROD or DEV]
OPENAI_TOKEN=your-openai-token
GOOGLE_SERVICE_ACCOUNT_FILE=your-google-developer-app-token
```

## Deployment
*Only if setting up a new bot*

The app is deployed on Heroku and uses the `deploy_bot.sh` script to deploy the application to different environments (dev and prod) based on the Git branch. 

### Prerequisites

- **Heroku Account**: You need a Heroku account to deploy and manage the app.
- **Telegram Bot API Token**: You need to generate a bot token from [BotFather](https://core.telegram.org/bots#botfather) on Telegram.


### Deploying the App

1. Clone the repository:

   ```bash
   git clone https://github.com/seeker-seventy-six/tirzhelp-bot.git
   cd tirzhelp-bot
   ```

2. **Deploy via Git Branch**:

   Use the `deploy_bot.sh` script to deploy to different Heroku environments (e.g., `dev` or `prod`) based on your Git branch.

     ```bash
     ./deploy_bot.sh
     ```

   The script will automatically detect the branch you're on and deploy the app accordingly.

### Automating Deployment with GitHub

To set up automated deployments:

1. **Link GitHub with Heroku**:
   - Go to your Heroku app's dashboard.
   - Under the "Deploy" tab, connect your GitHub repository.
   - Enable **Automatic Deploys** for the relevant branch (e.g., `main` or `dev`).

2. **Merge Requests**:
   - Whenever changes are merged into the selected branch (e.g., `main` or `dev`), Heroku will automatically deploy the app.

### Webhook Setup

After deployment, you need to set the webhook URL for the Telegram Bot API.

To set the webhook:

```bash
heroku run python bot.py setwebhook
```

This command sets the webhook URL for your bot to the Heroku app's URL.

## Bot Functionality

### **Commands**

- `/newbie`: Sends a welcome message manually.
- `/lastcall`: Sends a last call message for group tests (based on `lastcall` function).
- `/safety`: Sends a safety message (based on `safety` function).

## Debugging with Heroku CLI

You can debug any errors that occur on your Heroku app using the following Heroku CLI commands.

### **Login to Heroku**

To log in to Heroku, use the following command:

```bash
heroku login
```

This will open a browser window where you can log in to your Heroku account.

### **Tail Logs**

To view the live logs of your app, run:

```bash
heroku logs --tail --app "[app name]"
```

This will stream the logs, allowing you to monitor any issues or errors in real time.

### **Common Errors**

- **Missing Environment Variables**: Ensure your `.env-dev` and `.env-main` files contains the correct variables (`BOT_TOKEN`, `WEBHOOK_URL`, etc.). (NOTE: If developing on the existing bot, these can be found on the Heroku under Dashboard > [Application Name] > Settings > Config Vars)
- **Webhook Issues**: If your webhook is not working, check if the URL is correctly set by inspecting the logs.

## Conclusion

This Heroku app leverages the Telegram Bot API for user interaction and integrates with various Telegram groups and channels. You can easily deploy and manage different environments (dev/prod) using Git branches, and you have full access to error logs via Heroku CLI for troubleshooting.

---

## Discord Server Backup Template
https://discord.new/EDzNm6Gzz9S3