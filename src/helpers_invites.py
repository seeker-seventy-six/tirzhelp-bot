import json
import logging
import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterable, List, Optional, Union


import requests
from dotenv import load_dotenv


INVITE_MARKER = "[tg-invite-rotation]"
## (INVITE_COUNT x INVITE_MEMBER_LIMIT) should stay under about 3000 per 24 hours to avoid triggering nuke
INVITE_COUNT = 2
INVITE_MEMBER_LIMIT = 1000
DISCORD_API_BASE = "https://discord.com/api/v10"


_TELEGRAM_API_BASE: Optional[str] = None
_INVITE_CHAT_ID: Optional[str] = None
_rotation_thread: Optional[threading.Thread] = None

# Load environment variables
ENV_FILE = ".env-dev"
if os.path.exists(ENV_FILE):
    logging.info(f"Loading environment variables from {ENV_FILE}")
    load_dotenv(ENV_FILE, override=True)
else:
    logging.info("No local env file found; relying on OS / Heroku env vars.")

def _ensure_telegram_config():
    """Lazy-load Telegram API base URL and invite target chat ID."""
    global _TELEGRAM_API_BASE, _INVITE_CHAT_ID
    if _TELEGRAM_API_BASE and _INVITE_CHAT_ID:
        return

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN must be set to rotate Telegram invite links")
    _TELEGRAM_API_BASE = f"https://api.telegram.org/bot{bot_token}"

    telegram_config_json = os.getenv("TELEGRAM_CONFIG")
    if not telegram_config_json:
        raise RuntimeError("TELEGRAM_CONFIG must be set to determine invite target chat")

    try:
        telegram_config = json.loads(telegram_config_json)
        supergroup_id = telegram_config["SUPERGROUP_ID"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError("TELEGRAM_CONFIG must include SUPERGROUP_ID to rotate invites") from exc

    _INVITE_CHAT_ID = str(supergroup_id)


def create_invite_links(expire_seconds: int, count: int = 1, members_per_link: int = 1000) -> List[dict]:
    """Create Telegram invite links for the configured chat.

    Parameters
    ----------
    expire_seconds:
        How long each invite should remain valid, in seconds.
    count:
        Number of invites to create. Defaults to 1 but can be increased to
        support multiple concurrent links in the future.
    """
    _ensure_telegram_config()

    invites: List[dict] = []
    invite_count = max(1, int(count))

    for idx in range(invite_count):
        payload = {
            "chat_id": _INVITE_CHAT_ID,
            "expire_date": int(time.time()) + expire_seconds,
            "creates_join_request": False,
            "member_limit": members_per_link,
        }


        try:
            response = requests.post(
                f"{_TELEGRAM_API_BASE}/createChatInviteLink",
                json=payload,
                timeout=15,
            )
            data = response.json()
        except Exception as exc:
            logging.error("Error creating invite link %d/%d: %s", idx + 1, invite_count, exc)
            continue

        if response.ok and data.get("ok") and data.get("result"):
            invites.append(data["result"])
        else:
            logging.error(
                "Failed to create invite link %d/%d: %s",
                idx + 1,
                invite_count,
                data,
            )

    return invites


def revoke_invite_links(invite_links: Iterable[Union[str, dict]]):
    """Revoke previously created Telegram invite links."""
    _ensure_telegram_config()

    for link in invite_links:
        invite_url = link.get("invite_link") if isinstance(link, dict) else str(link)
        if not invite_url:
            continue

        try:
            response = requests.post(
                f"{_TELEGRAM_API_BASE}/revokeChatInviteLink",
                json={"chat_id": _INVITE_CHAT_ID, "invite_link": invite_url},
                timeout=15,
            )
            data = response.json()
            if not response.ok or not data.get("ok"):
                logging.warning("Failed to revoke invite %s: %s", invite_url, data)
        except Exception as exc:
            logging.warning("Error revoking invite %s: %s", invite_url, exc)


def _discord_headers() -> dict:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN must be set to post invite links to Discord")
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }


def _delete_previous_invite_messages(channel_id: str, marker: str):
    try:
        response = requests.get(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            params={"limit": 50},
            headers=_discord_headers(),
            timeout=15,
        )
        response.raise_for_status()
        messages = response.json()
    except Exception as exc:
        logging.error("Failed to fetch Discord messages for invite cleanup: %s", exc)
        return

    for message in messages:
        content = message.get("content") or ""
        if marker not in content:
            continue
        message_id = message.get("id")
        if not message_id:
            continue
        try:
            delete_response = requests.delete(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}",
                headers=_discord_headers(),
                timeout=15,
            )
            if delete_response.status_code == 429:
                logging.warning("Rate limited when deleting Discord invite message; stopping cleanup")
                break
            delete_response.raise_for_status()
            logging.info("Deleted previous invite message %s", message_id)
        except Exception as exc:
            logging.warning("Failed to delete old invite message %s: %s", message_id, exc)


def format_invite_message(invite_links: List[dict], marker: str) -> str:
    est_timestamp = int(datetime.now().astimezone(ZoneInfo("America/New_York")).timestamp())

    lines = [
        marker,
        "\n📨 **Current STG Telegram Invite Links**",
        f"Last updated: <t:{est_timestamp}:F>",
        "",
    ]


    if not invite_links:
        lines.append("No invites available right now. Please check back soon.")
    else:
        for idx, link in enumerate(invite_links, start=1):
            url = link.get("invite_link") if isinstance(link, dict) else str(link)
            name = link.get("name") if isinstance(link, dict) else None
            display_name = f" ({name})" if name else ""
            lines.append(f"{idx}. {url}{display_name}")

    lines.append("\nThese links rotate automatically each day to keep the TG entrance secure and to mitigate nuke risk.")
    lines.append("If the links are currently not working, check back tomorrow!\n\n")
    return "\n".join(lines)


def post_invites_to_discord_root(invite_links: List[dict], marker: str = INVITE_MARKER):
    channel_id = os.getenv("DISCORD_ROOT_CHANNEL_ID")
    if not channel_id:
        logging.info("DISCORD_ROOT_CHANNEL_ID not set; skipping Discord invite post")
        return

    channel_id = str(channel_id)
    _delete_previous_invite_messages(channel_id, marker)

    content = format_invite_message(invite_links, marker)

    try:
        response = requests.post(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            headers=_discord_headers(),
            json={"content": content},
            timeout=15,
        )
        response.raise_for_status()
        logging.info("Posted %d new invite links to Discord root channel", len(invite_links))
    except Exception as exc:
        logging.error("Failed to post invite links to Discord: %s", exc)


def _rotation_loop(
    interval_hours: float,
    expire_days: int,
    revoke_previous: bool,
    marker: str,
    invite_count: int,
):
    previous_links: List[dict] = []
    expire_seconds = max(60, int(expire_days * 24 * 3600))

    while True:
        try:
            if revoke_previous and previous_links:
                logging.info("Revoking %d previous Telegram invite links", len(previous_links))
                revoke_invite_links(previous_links)
                previous_links = []

            logging.info(
                "Creating %d Telegram invite link(s) (expires in %d days)",
                invite_count,
                expire_days,
            )
            new_links = create_invite_links(
                expire_seconds=expire_seconds,
                count=invite_count,
                members_per_link=INVITE_MEMBER_LIMIT,
            )


            if new_links:
                post_invites_to_discord_root(new_links, marker)
                previous_links = list(new_links)
            else:
                logging.warning("No invite links were created in this rotation cycle")

        except Exception as exc:
            logging.error("Invite rotation cycle failed: %s", exc)

        sleep_seconds = max(300, int(interval_hours * 3600))
        logging.info("Invite rotation sleeping for %d seconds", sleep_seconds)
        time.sleep(sleep_seconds)


def start_invite_rotation_thread():
    """Start the background thread that rotates Telegram invite links."""
    global _rotation_thread

    interval_hours = 24
    expire_days = 2
    channel_id = os.getenv("DISCORD_ROOT_CHANNEL_ID")
    if not channel_id:
        logging.info("DISCORD_ROOT_CHANNEL_ID not set; invite rotation thread disabled")
        return

    if _rotation_thread and _rotation_thread.is_alive():
        logging.debug("Invite rotation thread already running")
        return

    revoke_previous = True
    marker = INVITE_MARKER
    invite_count = INVITE_COUNT

    logging.info(
        "Starting invite rotation thread: every %sh, expire=%sd, revoke_previous=%s, invites=%d",
        interval_hours,
        expire_days,
        revoke_previous,
        invite_count,
    )

    _rotation_thread = threading.Thread(
        target=_rotation_loop,
        args=(interval_hours, expire_days, revoke_previous, marker, invite_count),
        daemon=True,
        name="invite-rotation",
    )
    _rotation_thread.start()
