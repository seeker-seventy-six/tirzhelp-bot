# helpers_invites Integration Test

This directory contains integration tests that hit the *real* Telegram and Discord APIs. Only run these tests against test infrastructure that you control.

## Prerequisites

Set the following environment variables (or place them in `.env-dev` and load them before running `pytest`):

- `BOT_TOKEN`: Telegram bot token that has admin rights in the target supergroup.
- `TELEGRAM_CONFIG`: JSON string containing at least `SUPERGROUP_ID`, e.g. `{ "SUPERGROUP_ID": 1234567890123 }`.
- `DISCORD_BOT_TOKEN`: Discord bot token with permission to delete/post messages in the target channel.
- `DISCORD_ROOT_CHANNEL_ID`: Discord channel ID (string) where invite rotation messages live.

> ⚠️ **Important**: Use disposable/test Telegram groups and Discord channels; these tests create and revoke invites, and delete channel messages tagged with the test marker (`[tg-integration-test]`).

## Running

Run from the project root so that the `src/` package is on `PYTHONPATH`:

```bash
PYTHONPATH=. pytest tests/integration/test_helpers_invites_integration.py::test_create_and_revoke_telegram_invite_and_update_discord -q
```


The test will:
1. Create a short-lived Telegram invite link via `helpers_invites.create_invite_links`.
2. Post it to Discord via `helpers_invites.post_invites_to_discord_root`, deleting prior messages that contain the marker.
3. Revoke the invite via `helpers_invites.revoke_invite_links`.
4. Repeat the cycle with a second invite to ensure only one marker message remains.

The test prints the Discord message IDs and invite URLs as it progresses for easy verification.
