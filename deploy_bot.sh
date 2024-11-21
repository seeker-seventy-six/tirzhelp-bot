#!/bin/bash

# Exit on error
set -e

# Step 0: Detect the current Git branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ -z "$CURRENT_BRANCH" ]]; then
  echo "Error: Unable to detect the current Git branch. Ensure you are in a Git repository."
  exit 1
fi

# Map branch to environment and pipeline stage
if [[ "$CURRENT_BRANCH" == "dev" ]]; then
  ENV_FILE=".env-dev"
  echo "Detected 'dev' branch."
elif [[ "$CURRENT_BRANCH" == "main" ]]; then
  ENV_FILE=".env-main"
  echo "Detected 'main' branch."
else
  echo "Error: Unsupported branch '$CURRENT_BRANCH'. Only 'dev' and 'main' are supported."
  exit 1
fi

# Step 1: Load environment variables from .env file
if [[ ! -f $ENV_FILE ]]; then
  echo "Error: .env file not found. Please create a .env file with BOT_TOKEN and HEROKU_APP_NAME"
  exit 1
fi

# Source the .env file
export $(grep -v '^#' $ENV_FILE | xargs)

# Check required variables
if [[ -z "$BOT_TOKEN" || -z "$HEROKU_APP_NAME" ]]; then
  echo "Error: BOT_TOKEN and HEROKU_APP_NAME must be defined in the .env file."
  exit 1
fi

# Step 2: Check for required tools
if ! command -v heroku &>/dev/null; then
    echo "Heroku CLI not found. Please install it first."
    exit 1
fi

# Step 3: Create or use the Heroku app
echo "Creating Heroku app $HEROKU_APP_NAME..."
heroku create $HEROKU_APP_NAME || echo "App already exists. Skipping creation."

HEROKU_URL=$(heroku apps:info --app $HEROKU_APP_NAME | grep "Web URL" | awk '{print $3}')
if [[ -z "$HEROKU_URL" ]]; then
  echo "Error: Could not fetch Heroku app URL."
  exit 1
fi
echo "Heroku app URL is: $HEROKU_URL"

WEBHOOK_URL="${HEROKU_URL}webhook"
heroku config:set BOT_TOKEN=$BOT_TOKEN --app $HEROKU_APP_NAME
heroku config:set WEBHOOK_URL=$WEBHOOK_URL --app $HEROKU_APP_NAME

# Step 4: Configure the Telegram Webhook with the new URL
echo "Setting Telegram webhook..."
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${WEBHOOK_URL}\", \"allowed_updates\": [\"message\", \"chat_member\", \"new_chat_members\"]}"

# Step 5: Verify the webhook configuration
echo "Verifying webhook configuration..."
curl -X GET "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"

# Step 6: Update WEBHOOK_URL in the .env file with the Heroku URL
echo "Updating WEBHOOK_URL in $ENV_FILE..."
if grep -q "WEBHOOK_URL" "$ENV_FILE"; then
  # If WEBHOOK_URL already exists in the file, update it
  sed -i "s|^WEBHOOK_URL=.*|WEBHOOK_URL=$WEBHOOK_URL|" "$ENV_FILE"
else
  # If WEBHOOK_URL does not exist, append it
  echo "WEBHOOK_URL=\"$WEBHOOK_URL\"" >> "$ENV_FILE"
fi


echo "Deployment completed successfully!"
echo "Your bot is now live at: ${WEBHOOK_URL}"

# Step 7: Link GitHub repository to Heroku and Auto-Deploy
echo "To finish linking GitHub branch ${CURRENT_BRANCH} with Heroku visit the dashboard: https://dashboard.heroku.com/apps"