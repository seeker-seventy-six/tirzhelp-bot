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
import logging
import os
import time
from pathlib import Path
from typing import Dict, Tuple

import requests
from dotenv import load_dotenv

import src.helpers_invites as invites

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load .env-dev (or default .env) so tests pick up local credentials automatically.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env-dev"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()

DISCORD_API_BASE = "https://discord.com/api/v10"
INVITE_BATCH_SIZE = 2
INVITE_STATE_TEST_PATH = Path(__file__).resolve().parent / ".invite_rotation_test_state.json"

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


def _write_state_file(invite_urls: list[str]):
    payload = {
        "invite_links": invite_urls,
        "updated_at": str(time.time()),
    }
    INVITE_STATE_TEST_PATH.write_text(json.dumps(payload))


def _seed_previous_cycle(
    discord_token: str,
    discord_channel_id: str,
    marker: str,
    expire_seconds: int,
) -> list[dict]:
    """Create a previous batch of invites and post them to Discord without using rotate_invites_once."""

    previous_invites = invites.create_invite_links(
        expire_seconds=expire_seconds,
        count=INVITE_BATCH_SIZE,
        members_per_link=invites.INVITE_MEMBER_LIMIT,
    )
    assert previous_invites, "Failed to seed previous Telegram invites"

    previous_urls = [link.get("invite_link") for link in previous_invites if link.get("invite_link")]
    assert len(previous_urls) == len(previous_invites), "Seeded invite missing invite_link"

    _write_state_file(previous_urls)

    content = invites.format_invite_message(previous_invites, marker)
    response = requests.post(
        f"{DISCORD_API_BASE}/channels/{discord_channel_id}/messages",
        headers=_discord_headers(discord_token),
        json={"content": content},
        timeout=15,
    )
    response.raise_for_status()
    # give Discord a moment so the message is discoverable via the API before deletion
    time.sleep(2)
    return previous_invites


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
    expire_days = expire_seconds / (24 * 3600)
    marker = "[tg-integration-test]"

    if INVITE_STATE_TEST_PATH.exists():
        INVITE_STATE_TEST_PATH.unlink()

    try:
        # Seed a previous cycle so rotate_invites_once has something to revoke
        _seed_previous_cycle(
            discord_token,
            discord_channel_id,
            marker,
            expire_seconds,
        )

        invites_list = invites.rotate_invites_once(
            expire_days=expire_days,
            invite_count=INVITE_BATCH_SIZE,
            members_per_link=invites.INVITE_MEMBER_LIMIT,
            marker=marker,
            revoke_previous=True,
            post_to_discord=True,
            state_path=INVITE_STATE_TEST_PATH,
        )
        assert invites_list, "Expected rotate_invites_once to return at least one invite"
        invite_urls = [link.get("invite_link") for link in invites_list if link.get("invite_link")]
        assert len(invite_urls) == len(invites_list), "invite_link missing from Telegram response"

        time.sleep(2)  # give Discord a moment
        messages = _fetch_discord_messages(discord_token, discord_channel_id)
        latest_message = _assert_single_marker_message(messages, marker)
        _assert_invites_present(latest_message, invite_urls)
        print("Posted Discord message", latest_message.get("id"), "with invites", invite_urls)

        print(
            "Integration test completed; current invite batch remains active until next rotation run."
        )
    finally:
        if INVITE_STATE_TEST_PATH.exists():
            INVITE_STATE_TEST_PATH.unlink()
