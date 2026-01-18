"""Integration tests for helpers_invites.py hitting real Telegram & Discord APIs.

These tests are meant to run against *test* infrastructure only. They will:
1. Create real Telegram invite links for the configured SUPERGROUP_ID.
2. Post the invite(s) to the configured Discord channel, deleting any previous
   invite messages that contain the supplied marker.
3. Revoke the created Telegram invite(s).

Run selectively, e.g.:

    pytest tests/integration/test_helpers_invites_integration.py::test_create_and_revoke_telegram_invite_and_update_discord -q

Make sure the following environment variables are exported (or present in
.env-dev and loaded prior to running the tests):

- BOT_TOKEN
- TELEGRAM_CONFIG (JSON with SUPERGROUP_ID)
- DISCORD_BOT_TOKEN
- DISCORD_ROOT_CHANNEL_ID

Use throwaway chats/channels, because these tests create/delete live data.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Tuple

import requests
from dotenv import load_dotenv

import src.helpers_invites as invites

# Load .env-dev (or default .env) so tests pick up local credentials automatically.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env-dev"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()

DISCORD_API_BASE = "https://discord.com/api/v10"
INVITE_BATCH_SIZE = 2

_TELEGRAM_API_BASE: str | None = None
_INVITE_CHAT_ID: str | None = None


def _load_telegram_env() -> Tuple[str, str]:
    """Load Telegram configuration from environment variables.

    Returns (telegram_api_base, invite_chat_id).
    Raises AssertionError if required env vars are missing.
    """

    global _TELEGRAM_API_BASE, _INVITE_CHAT_ID

    if _TELEGRAM_API_BASE and _INVITE_CHAT_ID:
        return _TELEGRAM_API_BASE, _INVITE_CHAT_ID

    bot_token = os.getenv("BOT_TOKEN")
    telegram_config_json = os.getenv("TELEGRAM_CONFIG")

    assert bot_token, "BOT_TOKEN must be set for integration tests"
    assert telegram_config_json, "TELEGRAM_CONFIG must be set for integration tests"

    try:
        telegram_config: Dict[str, str] = json.loads(telegram_config_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise AssertionError("TELEGRAM_CONFIG must be valid JSON") from exc

    try:
        invite_chat_id = str(telegram_config["SUPERGROUP_ID"])
    except KeyError as exc:  # pragma: no cover - defensive
        raise AssertionError("TELEGRAM_CONFIG must include SUPERGROUP_ID") from exc

    _TELEGRAM_API_BASE = f"https://api.telegram.org/bot{bot_token}"
    _INVITE_CHAT_ID = invite_chat_id

    return _TELEGRAM_API_BASE, _INVITE_CHAT_ID


def _load_discord_env() -> Tuple[str, str]:
    """Load Discord configuration from environment variables.

    Returns (bot_token, channel_id).
    Raises AssertionError if required env vars are missing.
    """

    token = os.getenv("DISCORD_BOT_TOKEN")
    channel_id = os.getenv("DISCORD_ROOT_CHANNEL_ID")

    assert token, "DISCORD_BOT_TOKEN must be set for integration tests"
    assert channel_id, "DISCORD_ROOT_CHANNEL_ID must be set for integration tests"

    return token, str(channel_id)


def _discord_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }


def _fetch_discord_messages(token: str, channel_id: str, limit: int = 50):
    try:
        response = requests.get(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            params={"limit": limit},
            headers=_discord_headers(token),
            timeout=15,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - integration aid
        hint = (
            "Discord API returned {status} for channel {channel}.\n"
            "Verify DISCORD_ROOT_CHANNEL_ID and that the bot has permission to read the channel."
        ).format(status=response.status_code if 'response' in locals() else 'an error', channel=channel_id)
        raise AssertionError(hint) from exc
    return response.json()


def _assert_single_marker_message(messages, marker: str) -> dict:
    marker_messages = [m for m in messages if marker in (m.get("content") or "")]
    assert (
        len(marker_messages) == 1
    ), f"Expected exactly one marker message; found {len(marker_messages)}"

    return marker_messages[0]


def _assert_invites_present(message: dict, invite_urls: list[str]):
    content = message.get("content") or ""
    for url in invite_urls:
        assert url in content, f"Marker message is missing invite URL: {url}"


def test_create_and_revoke_telegram_invite_and_update_discord():
    """Full integration flow for Telegram invite rotation helpers.

    Steps:
    1. Create Telegram invite links.
    2. Post to Discord root channel (deleting old marker messages).
    3. Revoke the invite links via Telegram.
    4. Create a second batch of invites, post again, ensure only one marker message exists.

    Run only against disposable/test chats & channels.
    """

    telegram_base, invite_chat_id = _load_telegram_env()
    discord_token, discord_channel_id = _load_discord_env()

    expire_seconds = 600  # 10 minutes for test purposes
    marker = "[tg-integration-test]"

    # --- Step 1: create Telegram invite links ---
    invites_list = invites.create_invite_links(expire_seconds=expire_seconds, count=INVITE_BATCH_SIZE)
    assert invites_list, "Expected helpers_invites.create_invite_links to return at least one invite"
    invite_urls = [link.get("invite_link") for link in invites_list if link.get("invite_link")]
    assert len(invite_urls) == len(invites_list), "invite_link missing from Telegram response"

    # --- Step 2: post to Discord & verify the new marker message exists ---
    invites.post_invites_to_discord_root(invites_list, marker=marker)
    time.sleep(2)  # give Discord a moment

    messages = _fetch_discord_messages(discord_token, discord_channel_id)
    latest_message = _assert_single_marker_message(messages, marker)
    _assert_invites_present(latest_message, invite_urls)
    print("Posted Discord message", latest_message.get("id"), "with invites", invite_urls)

    # --- Step 3: revoke the Telegram invite links ---
    invites.revoke_invite_links(invites_list)
    time.sleep(2)  # give Telegram a moment

    # --- Step 4: create a second invite batch + post to Discord again ---
    second_invite_list = invites.create_invite_links(expire_seconds=expire_seconds, count=INVITE_BATCH_SIZE)
    assert second_invite_list, "Failed to create second Telegram invite batch"
    second_invite_urls = [link.get("invite_link") for link in second_invite_list if link.get("invite_link")]
    assert len(second_invite_urls) == len(second_invite_list), "Second invite batch missing invite_link"

    invites.post_invites_to_discord_root(second_invite_list, marker=marker)
    time.sleep(2)

    messages_after = _fetch_discord_messages(discord_token, discord_channel_id)
    final_message = _assert_single_marker_message(messages_after, marker)
    _assert_invites_present(final_message, second_invite_urls)
    print("After second post, only message", final_message.get("id"), "remains with invites", second_invite_urls)

    # Cleanup: revoke second invite batch so the test leaves no valid links (optional but polite)
    invites.revoke_invite_links(second_invite_list)
    time.sleep(2)

    # Verify Telegram cleanup (optional best-effort)
    for url in second_invite_urls:
        cleanup_check = requests.post(
            f"{telegram_base}/revokeChatInviteLink",
            json={"chat_id": invite_chat_id, "invite_link": url},
            timeout=15,
        )
        cleanup_data = cleanup_check.json()
        assert (
            cleanup_check.status_code == 400
            and cleanup_data.get("description", "").lower().startswith("bad request: invite link has already been revoked")
        ) or cleanup_data.get("ok"), (
            "Expected Telegram cleanup revoke to either succeed or report already revoked; "
            f"response was {cleanup_data}"
        )

    print("Integration test completed; all invite batches revoked and Discord state validated.")
