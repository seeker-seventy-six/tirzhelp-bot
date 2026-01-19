# Discord Bot Token / Channel Checklist

If the integration test fails with a 403/404 when reading or posting to Discord, work through the following:

1. **Confirm the bot token**
   - In the Discord Developer Portal, open your application and regenerate/copy the *Bot* token.
   - Update `.env-dev` or the relevant environment with the fresh `DISCORD_BOT_TOKEN`.
   - Restart any running bot processes that rely on the token.

2. **Ensure the bot is in the correct server**
   - Invite the bot to the server that owns `DISCORD_ROOT_CHANNEL_ID`.
   - In the server’s member list, confirm the bot appears and has a role with the necessary permissions.

3. **Check channel permissions**
   - Open the channel whose ID you set for `DISCORD_ROOT_CHANNEL_ID` (right-click > *Copy ID* with Developer Mode on).
   - In channel settings → Permissions, ensure the bot (or the role assigned to it) has:
     - View Channel
     - Send Messages
     - Manage Messages (needed so helpers can delete the old marker message)

4. **Validate the channel ID**
   - With Developer Mode enabled in Discord (User Settings → Advanced → Developer Mode), right-click the channel and choose “Copy ID”.
   - Paste this value into `DISCORD_ROOT_CHANNEL_ID` and redeploy/restart as needed.

5. **Manual API sanity check** (optional)
   - Use `curl` or Postman to hit `https://discord.com/api/v10/channels/{channel_id}/messages` with the `Authorization: Bot <token>` header.
   - A 200 response means the token/channel/permissions are correct; 403/404 indicates a mismatch you must fix first.

Once these checks pass, rerun:

```bash
PYTHONPATH=. pytest tests/integration/test_helpers_invites_integration.py::test_create_and_revoke_telegram_invite_and_update_discord --log-cli-level=INFO
```
