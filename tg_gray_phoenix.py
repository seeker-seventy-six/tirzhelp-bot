import os
import sys
import asyncio
import logging
from typing import List, Union, Optional, AsyncIterator
from dotenv import load_dotenv

from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserAlreadyParticipantError, ServerError, ChannelForumMissingError
from telethon.tl.functions.messages import ForwardMessagesRequest, UpdatePinnedMessageRequest
from telethon.tl.functions.channels import (
    CreateChannelRequest, 
    CreateForumTopicRequest, 
    ToggleForumRequest, 
    GetForumTopicsRequest,
    EditForumTopicRequest,
    InviteToChannelRequest,
    EditAdminRequest,
    EditPhotoRequest
)
from telethon.tl.types import (
    ChatAdminRights,
    InputPeerChannel,
    InputChannel,
    MessageService,
    UpdateNewChannelMessage,
    InputChatUploadedPhoto
)

"""Telegram group-clone helper
--------------------------------
• Creates a new supergroup with forum enabled
• Re-creates topics defined in TOPIC_FORWARD_MAP
• Forwards **all** messages from each source topic and pins **only** the
  ones explicitly listed in `messages`
"""

# -------------------------------------------------------------------
# 1) CONFIGURATION
# -------------------------------------------------------------------

# Load environment and configure logging
load_dotenv('.env-dev')
APP_ID = os.getenv("TELEGRAM_APP_ID")
APP_HASH = os.getenv("TELEGRAM_APP_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# Constants
SOURCE_SUPERGROUP_ID = -1002334662710
NEW_GROUP_TITLE = "Stairway to Gray 🐦‍🔥🐦‍🔥" 
NEW_GROUP_DESCRIPTION = "We help people with tirzepatide in the peptide community\nhttps://www.stairwaytogray.com"

USERS_TO_ADD = [
    'stg_help_bot',
    'seekerseventysix',
    'stg_stairmaster1',
    'delululemonade',
    'Steph_752501',
    'aksailor',
    'NordicTurtle',
    'Ruca2573',
    'Litajj',
    'UncleNacho',
    'ruttheimer',
    'QuestyQuestyQuesty',
    'justaturkey',
]

PINNED_TOPIC_NAMES = [
    "Rules & Guides - READ THIS FIRST", 
    "Announcements", 
    "Newbies - TIRZ & SEMA ONLY"
]

ADMIN_RIGHTS = ChatAdminRights(
    change_info=True,
    post_messages=True,
    edit_messages=True,
    delete_messages=True,
    ban_users=True,
    invite_users=True,
    pin_messages=True,
    add_admins=True,
    manage_call=True,
)

TOPIC_FORWARD_MAP = {
    "Rules & Guides - READ THIS FIRST": {
        "messages": [], 
        "icon_color": 0xFFD700,        # Gold
        "icon_emoji_id": 5350481781306958339         
    },
    "Announcements": {
        "messages": [],
        "icon_color": 0xFF8C00,        # DarkOrange
        "icon_emoji_id": 5377498341074542641
    },
    "Newbies - TIRZ & SEMA ONLY": {
        "messages": ['3052'],
        "icon_color": 0x009688,        # Material Teal
        "icon_emoji_id": 5377675010259297233
    },
    "Test Results - NO DISCUSSION": {
        "messages": ['1238'], 
        "icon_color": 0x9C27B0,        # Material Purple
        "icon_emoji_id": 5373251851074415873
    },
    "Group Test Invites - NO DISCUSSION": {
        "messages": ['3046','3048'],
        "icon_color": 0x4CAF50,        # Material Green
        "icon_emoji_id": 5357315181649076022
    },
    "Sources & Testing": {
        "messages": ['1229','1231'],
        "icon_color": 0xE91E63,        # Material Pink
        "icon_emoji_id": 5362079447136610876
    },
    "Vendor Promos": {
        "messages": ['2086'],
        "icon_color": 0xF08500,        # Orange-ish
        "icon_emoji_id": 5208801655004350721
    },
    "Supplies, Storage, & Labels": {
        "messages": ['3053'],
        "icon_color": 0x8BC34A,        # Light Green
        "icon_emoji_id": 5377660214096974712
    },
    "Other Peptides & Reconstituting": {
        "messages": ['2708'],
        "icon_color": 0x3F51B5,        # Indigo
        "icon_emoji_id": 5411138633765757782
    },
    "Science": {
        "messages": ['2092','3054','3006'],
        "icon_color": 0x673AB7,        # Deep Purple
        "icon_emoji_id": 5190406357320216268
    },
    "PenPorium": {
        "messages": [],
        "icon_color": 0x795548,        # Brown
        "icon_emoji_id": 5208782954716733247
    },
    "International": {
        "messages": ['2702'],
        "icon_color": 0x607D8B,        # Blue Grey
    },
    "Raffle & Fun": {
        "messages": [],
        "icon_color": 0xCDDC39,        # Lime
        "icon_emoji_id": 5449698107119904829
    },
    "Progress Pics": {
        "messages": [],
        "icon_color": 0xFFC107,        # Amber
        "icon_emoji_id": 5235837920081887219
    },
    "Food, Nutrition, & Fitness": {
        "messages": [],
        "icon_color": 0xFF5722,        # Deep Orange
        "icon_emoji_id": 5395463497783983254
    },
    "Pets!": {
        "messages": [],
        "icon_color": 0xFFB6C1,        # LightPink
        "icon_emoji_id": 5235912661102773458
    }
}

# ─────────────────────────────────────── ENV/LOGGING ──────────────────────────────────────
load_dotenv(".env-dev")
APP_ID, APP_HASH, PHONE = os.getenv("TELEGRAM_APP_ID"), os.getenv("TELEGRAM_APP_HASH"), os.getenv("PHONE_NUMBER")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", stream=sys.stdout)

# ───────────────────────────────────────── MAIN ───────────────────────────────────────────
async def main():
    client = TelegramClient("clone_session", APP_ID, APP_HASH)
    await client.start(phone=PHONE)
    logging.info("Telegram session opened")

    # create new group (retry around CHAT_OCCUPY_LOC_FAILED)
    logging.info("[STEP] Creating new group…")
    new_group = await create_group_with_retry(client)
    if not new_group:
        logging.error("Group creation failed; aborting")
        return
    logging.info("[STEP] New group created as forum-enabled megagroup (via CreateChannelRequest).")

    logging.info("[STEP] Renaming and locking General topic…")
    await rename_and_lock_general(client, new_group)

    logging.info(f"[STEP] Fetching source supergroup {SOURCE_SUPERGROUP_ID}…")
    src_entity = await client.get_entity(SOURCE_SUPERGROUP_ID)
    src_peer   = InputPeerChannel(src_entity.id, src_entity.access_hash)
    dst_peer   = InputPeerChannel(new_group.id, new_group.access_hash)

    logging.info("[STEP] Building source topic map…")
    src_topic_map = await build_topic_map(client, src_entity)

    logging.info("[STEP] Setting logo on destination group…")
    await set_logo(client, "./stairway-to-gray-logo.png", dst_peer)

    logging.info("[STEP] Adding admins to destination group…")
    await add_admins(client, dst_peer)

    logging.info("[STEP] Creating destination topics and migrating messages…")
    # create + migrate topics
    for title, cfg in TOPIC_FORWARD_MAP.items():
        logging.info(f"[TOPIC] Creating/migrating '{title}'…")
        dst_topic = await create_topic_and_pin_if_needed(client, new_group, title, cfg)
        if not dst_topic:
            logging.warning(f"[TOPIC] Skipping '{title}' because destination topic was not created/found")
            continue

        src_topic_id = src_topic_map.get(title)
        if src_topic_id:
            await migrate_messages(client, src_peer, dst_peer, src_topic_id, dst_topic, cfg["messages"])
        else:
            logging.info(f"[TOPIC] '{title}' not found in source — created empty")

    logging.info("[STEP] Disconnecting client…")
    await client.disconnect()
    logging.info("✅ Done – new group ready")

# ──────────────────────────────────── HELPERS ─────────────────────────────────────────────
async def create_group_with_retry(client, tries=5):
    for n in range(1, tries+1):
        try:
            grp = await client(CreateChannelRequest(
                title=NEW_GROUP_TITLE,
                about=NEW_GROUP_DESCRIPTION,
                megagroup=True,
                forum=True,
            ))
            logging.info(f"Created group '{NEW_GROUP_TITLE}' on attempt {n}")
            return grp.chats[0]
        except ServerError as e:
            logging.warning(f"{e} (attempt {n}/{tries}) – retrying in 30 s")
            await asyncio.sleep(30)
    return None

async def build_topic_map(client, channel):
    res = await client(GetForumTopicsRequest(channel=channel, offset_date=0, offset_id=0, offset_topic=0, limit=100))
    return {t.title: t.id for t in res.topics}

async def create_topic_and_pin_if_needed(
    client,
    new_group,
    topic_name,
    cfg
):
    """
    Creates a forum topic in 'new_group' titled 'topic_name'.
    If 'topic_name' is in PINNED_TOPIC_NAMES, we also pin the topic.

    Returns the newly created topic object (or None if not found).
    """
    # 1) Create the topic
    create_topic_req = CreateForumTopicRequest(
        channel=new_group,
        title=topic_name,
        icon_color=cfg.get('icon_color', None),
        icon_emoji_id=cfg.get('icon_emoji_id', None),
    )
    await safe(client, create_topic_req)
    await asyncio.sleep(1.0)

    # 2) Fetch the current list of topics to find the newly created one
    topics_result = await client(GetForumTopicsRequest(
        channel=new_group,
        offset_date=0,
        offset_id=0,
        offset_topic=0,
        limit=50
    ))

    new_topic = None
    for t in topics_result.topics:
        if t.title == topic_name:
            new_topic = t
            break

    if not new_topic:
        logging.warning(f"Could not locate newly created topic '{topic_name}'.")
        return None

    logging.info(f"Created dest topic '{topic_name}' with ID = {new_topic.id}")

    # 3) Optionally pin the topic if it's in our pinned list
    if topic_name in PINNED_TOPIC_NAMES:
        logging.info(f"Pinning topic '{topic_name}'...")
        try:
            new_topic_pin_req = EditForumTopicRequest(
                channel=new_group,
                topic_id=new_topic.id,
                pinned=True
            )
            await safe(client, new_topic_pin_req)
            await asyncio.sleep(1.0)
        except Exception as e:
            logging.warning(f"Failed to pin topic '{topic_name}': {e}")

    return new_topic

async def iter_topic_message_ids(
    client: TelegramClient,
    chat: Union[int, str, InputChannel],
    topic_id: int,
    limit: Optional[int] = None,
) -> AsyncIterator[int]:
    """Yield message-ids (oldest → newest) from one forum topic."""
    async for msg in client.iter_messages(
        chat,
        reply_to=topic_id,
        limit=limit,
        reverse=True,         # oldest first
    ):
        if not isinstance(msg, MessageService):
            yield int(msg.id)

async def migrate_messages(client, src_peer, dst_peer, src_topic_id, dst_topic, pin_ids):
    top_msg_id = dst_topic.top_message
    pin_set = {int(i) for i in pin_ids}

    async for src_mid in iter_topic_message_ids(client, src_peer, src_topic_id):
        fwd = await safe(client, ForwardMessagesRequest(from_peer=src_peer, id=[src_mid], to_peer=dst_peer, top_msg_id=top_msg_id, silent=True, drop_author=False))
        if not fwd:
            logging.warning(f"Failed to forward src#{src_mid} to dst#{dst_peer} (src topic {src_topic_id})")
            continue
        new_id = next((int(u.message.id) for u in fwd.updates if isinstance(u, UpdateNewChannelMessage)), None)
        if new_id and src_mid in pin_set:
            await safe(client, UpdatePinnedMessageRequest(peer=dst_peer, id=new_id, silent=True))
            logging.info(f"📌 pinned src#{src_mid} → dst#{new_id}")
            await asyncio.sleep(5.0)

async def rename_and_lock_general(client, group):
    try:
        res = await client(GetForumTopicsRequest(channel=group, offset_date=0, offset_id=0, offset_topic=0, limit=10))
    except ChannelForumMissingError:
        logging.warning("[WARN] Channel does not have forum enabled; skipping rename_and_lock_general.")
        return
    gen = next((t for t in res.topics if t.title == "General"), None)
    if gen:
        await safe(client, EditForumTopicRequest(channel=group, topic_id=gen.id, title="Welcome"))
        await safe(client, EditForumTopicRequest(channel=group, topic_id=gen.id, closed=True))

async def set_logo(client, path, peer):
    photo = await client.upload_file(path)
    await safe(client, EditPhotoRequest(channel=peer, photo=InputChatUploadedPhoto(photo)))

async def add_admins(client, peer):
    for user in USERS_TO_ADD:
        try:
            ent = await client.get_entity('@'+user)
            try:
                await client(InviteToChannelRequest(channel=peer, users=[ent]))
            except UserAlreadyParticipantError:
                pass
            await client(EditAdminRequest(channel=peer, user_id=ent, admin_rights=ADMIN_RIGHTS, rank="Admin"))
            logging.info(f"Admin ✓ {user}")
        except Exception as exc:
            logging.warning(f"Admin add failed for {user}: {exc}")

async def safe(client, req):
    while True:
        try:
            return await client(req)
        except FloodWaitError as e:
            if e.seconds > 300:
                logging.warning(f"FloodWait {e.seconds}s – skipping")
                return None
            logging.warning(f"FloodWait {e.seconds}s – sleep")
            await asyncio.sleep(e.seconds)

# ───────────────────────────────────────────────────────────────────
# 9) ENTRY
# ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
