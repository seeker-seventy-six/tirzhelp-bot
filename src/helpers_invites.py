import argparse
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Union
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

INVITE_MARKER = "[tg-invite-rotation]"
## (INVITE_COUNT x INVITE_MEMBER_LIMIT) should stay under about 3000 per 24 hours to avoid triggering nuke
INVITE_COUNT = 2
INVITE_MEMBER_LIMIT = 1000
DISCORD_API_BASE = "https://discord.com/api/v10"
INVITE_STATE_PATH = Path(os.getenv("INVITE_STATE_PATH", ".invite_rotation_state.json")).expanduser()

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

def _normalize_invite_link(link: Union[str, dict, None]) -> Optional[str]:
    if isinstance(link, dict):
        return link.get("invite_link")
    if link:
        return str(link)
    return None

def _load_stored_invite_links(state_path: Optional[Path] = None) -> List[str]:
    path = state_path or INVITE_STATE_PATH
    try:
        raw = path.read_text().strip()
    except FileNotFoundError:
        return []
    except Exception as exc:  # pragma: no cover - defensive
        logging.warning("Unable to read invite rotation state %s: %s", path, exc)
        return []

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        logging.warning("Invite rotation state %s is invalid JSON: %s", path, exc)
        return []

    if isinstance(data, dict):
        invite_links = data.get("invite_links", [])
    elif isinstance(data, list):
        invite_links = data
    else:
        invite_links = []

    cleaned: List[str] = []
    for link in invite_links:
        if isinstance(link, str) and link:
            cleaned.append(link)
    return cleaned

def _persist_invite_links(
    invite_links: Iterable[Union[str, dict]], state_path: Optional[Path] = None
) -> None:
    path = state_path or INVITE_STATE_PATH
    if not path:
        return

    normalized: List[str] = []
    for link in invite_links:
        invite_url = _normalize_invite_link(link)
        if invite_url:
            normalized.append(invite_url)

    payload = {
        "invite_links": normalized,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        logging.debug("Persisted %d invite link(s) to %s", len(normalized), path)
    except Exception as exc:  # pragma: no cover - defensive
        logging.warning("Unable to persist invite rotation state to %s: %s", path, exc)

def create_invite_links(expire_seconds: int, count: int = 1, members_per_link: int = 1000) -> List[dict]:
    """Create Telegram invite links for the configured chat."""
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
            invite = data["result"]
            invite_url = invite.get("invite_link")
            logging.info("Created invite %d/%d: %s", idx + 1, invite_count, invite_url)
            invites.append(invite)
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
        invite_url = _normalize_invite_link(link)
        if not invite_url:
            continue

        try:
            response = requests.post(
                f"{_TELEGRAM_API_BASE}/revokeChatInviteLink",
                json={"chat_id": _INVITE_CHAT_ID, "invite_link": invite_url},
                timeout=15,
            )
            data = response.json()
            if response.ok and data.get("ok"):
                logging.info("Revoked invite: %s", invite_url)
            else:
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

    lines.append(
        "\nThese links rotate automatically each day to keep the TG entrance secure and to mitigate nuke risk."
    )
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

    invite_urls = [link.get("invite_link") for link in invite_links if isinstance(link, dict)]
    logging.info("Posting invites to Discord: %s", invite_urls)

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

def rotate_invites_once(
    *,
    expire_days: float = 2,
    invite_count: int = INVITE_COUNT,
    members_per_link: int = INVITE_MEMBER_LIMIT,
    marker: str = INVITE_MARKER,
    revoke_previous: bool = True,
    post_to_discord: bool = True,
    state_path: Optional[Union[str, Path]] = None,
) -> List[dict]:
    """Rotate Telegram invite links a single time and optionally persist the latest batch."""

    state_file = Path(state_path).expanduser() if state_path else INVITE_STATE_PATH
    previous_stored = _load_stored_invite_links(state_file)
    revoke_queue = list(previous_stored) if revoke_previous and previous_stored else []

    expire_seconds = max(60, int(expire_days * 24 * 3600))
    new_links = create_invite_links(
        expire_seconds=expire_seconds,
        count=invite_count,
        members_per_link=members_per_link,
    )

    if not new_links:
        logging.warning("rotate_invites_once: no invite links were created")
        return []

    if post_to_discord:
        post_invites_to_discord_root(new_links, marker)

    if revoke_queue:
        logging.info(
            "Revoking %d previously stored invite link(s) after posting new batch",
            len(revoke_queue),
        )
        revoke_invite_links(revoke_queue)

    _persist_invite_links(new_links, state_file)
    return new_links

def _rotation_loop(
    *,
    expire_days: float,
    revoke_previous: bool,
    marker: str,
    invite_count: int,
    interval_hours: float,
    initial_delay_seconds: float,
    state_path: Optional[Path],
):
    if initial_delay_seconds > 0:
        logging.info(
            "Invite rotation initial delay: sleeping for %s seconds before first cycle",
            initial_delay_seconds,
        )
        time.sleep(initial_delay_seconds)

    while True:
        try:
            rotate_invites_once(
                expire_days=expire_days,
                invite_count=invite_count,
                members_per_link=INVITE_MEMBER_LIMIT,
                marker=marker,
                revoke_previous=revoke_previous,
                post_to_discord=True,
                state_path=state_path,
            )
        except Exception as exc:
            logging.error("Invite rotation cycle failed: %s", exc)

        sleep_seconds = max(300, int(interval_hours * 3600))
        logging.info("Invite rotation sleeping for %d seconds", sleep_seconds)
        time.sleep(sleep_seconds)

def start_invite_rotation_thread():
    """Start the background thread that rotates Telegram invite links."""
    global _rotation_thread

    interval_hours = float(os.getenv("INVITE_ROTATION_INTERVAL_HOURS", 24))
    expire_days = float(os.getenv("INVITE_ROTATION_EXPIRE_DAYS", 2))
    initial_delay_seconds = float(os.getenv("INVITE_ROTATION_INITIAL_DELAY_SECONDS", 0))
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
    state_path = INVITE_STATE_PATH

    logging.info(
        "Starting invite rotation thread: every %sh, expire=%sd, revoke_previous=%s, invites=%d, initial_delay=%ss",
        interval_hours,
        expire_days,
        revoke_previous,
        invite_count,
        initial_delay_seconds,
    )

    _rotation_thread = threading.Thread(
        target=_rotation_loop,
        kwargs={
            "expire_days": expire_days,
            "revoke_previous": revoke_previous,
            "marker": marker,
            "invite_count": invite_count,
            "interval_hours": interval_hours,
            "initial_delay_seconds": initial_delay_seconds,
            "state_path": state_path,
        },
        daemon=True,
        name="invite-rotation",
    )

    _rotation_thread.start()
