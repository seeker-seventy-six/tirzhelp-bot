# 🤖 TirzHelpBot
*A Telegram Bot API Heroku App for r/TirzepatideHelp*

This is a Flask-based application that integrates with the Telegram Bot API. It allows you to interact with Telegram supergroups and handle commands from users. The bot is set up with a webhook to process incoming updates and respond accordingly.

Once the bot is deployed to Heroku and added as a member to a Telegram supergroup or group chat, it can be used for the following features.

## Features

- **User Login Verification**: Verifies if a user is a member of a specific Telegram supergroup using the `login` route.
- **Webhook Handling**: Listens to incoming updates and processes commands like `/newbie`, `/lastcall`, and `/safety`.
- **Automatic Welcome**: Welcomes new users when they join specific supergroups.
- **Banned Topic Filtering**: Filters messages for banned topics and alerts the user if a topic is found.
- **Document Summarization**: Summarizes test results from uploaded documents in the designated test results channels.

## Deployment

The app is deployed on Heroku and uses the `deploy_bot.sh` script to deploy the application to different environments (dev and prod) based on the Git branch. 

### Prerequisites

- **Heroku Account**: You need a Heroku account to deploy and manage the app.
- **Telegram Bot API Token**: You need to generate a bot token from [BotFather](https://core.telegram.org/bots#botfather) on Telegram.

### Environment Setup

Before deploying, create a `.env-dev` and `.env-prod` file with the following environment variables for each bot environment:

```
BOT_TOKEN=your-telegram-bot-token
WEBHOOK_URL=https://your-heroku-app-url/webhook
```

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

## Webhook Setup

After deployment, you need to set the webhook URL for the Telegram Bot API.

To set the webhook:

```bash
heroku run python bot.py setwebhook
```

This command sets the webhook URL for your bot to the Heroku app's URL.

## Bot Functionality

### **1. `/login` Route**

This route is used to verify if a user is part of a specific supergroup.

- **Request**: 
  ```
  GET /login?user_id=<user_id>
  ```
- **Response**: 
  - `200 OK` if the user is a member of the supergroup.
  - `403 Forbidden` if the user is not a member.

The function uses the helper `helpers_telegram.is_user_in_supergroup(user_id)` to check the user’s membership in the supergroup.

### **2. `/setwebhook` Route**

Sets the webhook for your bot with the provided `WEBHOOK_URL`.

- **Request**: 
  ```
  GET /setwebhook
  ```
- **Response**: 
  - Success response with the status of the webhook setup.

This route triggers a POST request to Telegram's API to set the webhook for your bot.

### **3. `/webhook` Route**

Handles incoming messages and updates sent to the bot. This is the main endpoint where Telegram will send updates.

- **Request**: 
  ```
  POST /webhook
  ```
- **Processing**:
  - If a new member joins the group, it sends an automatic welcome message in #Welcome channel.
  - It processes commands such as `/newbie`, `/lastcall`, and `/safety`.
  - Automatically responds to banned topics (e.g., "DNP" for Dinitrophenol) in all channels.
  - Summarizes test results if documents or photos are uploaded in the specified #Test Results channel.
  - Automatically posts an hourly Newbie Announcement in Newbies channel.

### **Commands**

- `/newbie`: Sends a welcome message to new users.
- `/lastcall`: Sends a last call message (based on `lastcall` function).
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
heroku logs --tail
```

This will stream the logs, allowing you to monitor any issues or errors in real time.

### **Common Errors**

- **Missing Environment Variables**: Ensure your `.env` file contains the correct variables (`BOT_TOKEN`, `WEBHOOK_URL`).
- **Webhook Issues**: If your webhook is not working, check if the URL is correctly set by inspecting the logs.

## Conclusion

This Heroku app leverages the Telegram Bot API for user interaction and integrates with various Telegram groups and channels. You can easily deploy and manage different environments (dev/prod) using Git branches, and you have full access to error logs via Heroku CLI for troubleshooting.

---

## Discord Server Backup Template
https://discord.new/EDzNm6Gzz9S3