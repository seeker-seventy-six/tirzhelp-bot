from dotenv import load_dotenv
import os
import sys
import logging
import asyncio

from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
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
    UpdateNewChannelMessage,
    InputChatUploadedPhoto
)

# -------------------------------------------------------------------
# 1) CONFIGURATION
# -------------------------------------------------------------------
SOURCE_SUPERGROUP_ID = -1002334662710 
NEW_GROUP_TITLE = "GrayPhoenix::TestGroup"
NEW_GROUP_DESCRIPTION = (
    "We help people with tirzepatide in the gray peptide community\n"
    "https://www.stairwaytogray.com"
)
USERS_TO_ADD = [
    '@tirzhelp_bot',
    '@aksailor',
    '@boo_7777',
    '@NordicTurtle',
    '@tirzepatidehelp',
    '@stephs2125',
    '@Ruca2573',
    '@Litajj',
    '@delululemonade',
]
# Define which admin rights you want them to have
ADMIN_RIGHTS = ChatAdminRights(
    change_info=True,
    post_messages=True,
    edit_messages=True,
    delete_messages=True,
    ban_users=True,
    invite_users=True,
    pin_messages=True,
    add_admins=True,   # Set True if you want them to also add admins
    manage_call=True,
)

TOPIC_FORWARD_MAP = {
    "Rules & Guides": {
        "messages": ['1226','1227'],
        "icon_color": 0xFFD700,        # Gold
        "icon_emoji_id": 5350481781306958339         
    },
    "Announcements": {
        "messages": ['1224'],
        "icon_color": 0xFF8C00,        # DarkOrange
        "icon_emoji_id": 5377498341074542641
    },
    "Newbies": {
        "messages": [],
        "icon_color": 0x009688,        # Material Teal
        "icon_emoji_id": 5377675010259297233
    },
    "General": {
        "messages": [],
        "icon_color": 0x2196F3,        # Material Blue
        "icon_emoji_id": 5316705050389670171
    },
    "Test Results - NO DISCUSSION": {
        "messages": ['1238','1239'],
        "icon_color": 0x9C27B0,        # Material Purple
        "icon_emoji_id": 5373251851074415873
    },
    "Group Test Invites - NO DISCUSSION": {
        "messages": ['1241','1242'],
        "icon_color": 0x4CAF50,        # Material Green
        "icon_emoji_id": 5357315181649076022
    },
    "Sources & Testing": {
        "messages": ['1229','1230','1231'],
        "icon_color": 0xE91E63,        # Material Pink
        "icon_emoji_id": 5362079447136610876
    },
    "Vendor Promos": {
        "messages": ['1244'],
        "icon_color": 0xF08500,        # Orange-ish
        "icon_emoji_id": 5208801655004350721
    },
    "Supplies, Storage, & Labels": {
        "messages": ['1233','1234'],
        "icon_color": 0x8BC34A,        # Light Green
        "icon_emoji_id": 5377660214096974712
    },
    "Other Peptides & Reconstituting": {
        "messages": ['1247','1248','1249'],
        "icon_color": 0x3F51B5,        # Indigo
        "icon_emoji_id": 5411138633765757782
    },
    "PenPorium": {
        "messages": [],
        "icon_color": 0x795548,        # Brown
        "icon_emoji_id": 5208782954716733247
    },
    "Science": {
        "messages": [],
        "icon_color": 0x673AB7,        # Deep Purple
        "icon_emoji_id": 5190406357320216268
    },
    "Raffle & Fun": {
        "messages": [],
        "icon_color": 0xCDDC39,        # Lime
        "icon_emoji_id": 5449698107119904829
    },
    "Progress & Pics": {
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

load_dotenv('.env-dev')
APP_ID = os.getenv("TELEGRAM_APP_ID")
APP_HASH = os.getenv("TELEGRAM_APP_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    stream=sys.stdout
)

# -------------------------------------------------------------------
# 2) SCRIPT (ASYNC)
# -------------------------------------------------------------------
async def main():
    client = TelegramClient("my_session", APP_ID, APP_HASH)
    await client.start(phone=PHONE_NUMBER)
    logging.info("Telegram Session opened...")

    # (1) Create a new supergroup (default "General" topic is auto-created once we enable Forum mode)
    result = await client(CreateChannelRequest(
        title=NEW_GROUP_TITLE,
        about=NEW_GROUP_DESCRIPTION,
        megagroup=True
    ))
    new_group = result.chats[0]
    logging.info(f"Created supergroup: {new_group.title} (ID={new_group.id})")

    # (2) Enable forum (topics) in the new group
    toggle_forum_req = ToggleForumRequest(
        channel=new_group,
        enabled=True
    )
    await safe_telethon_call(client, toggle_forum_req)
    await asyncio.sleep(1.0)

    # (3) Rename General to Welcome and close topic
    await rename_and_lock_general(client, new_group)

    # (4) Now proceed to create our additional topics and forward messages
    source_entity = await client.get_entity(SOURCE_SUPERGROUP_ID)
    source_peer = InputPeerChannel(source_entity.id, source_entity.access_hash)
    destination_peer = InputPeerChannel(new_group.id, new_group.access_hash)

    # Set telegram logo picture for group
    await set_logo(client, './stairway-to-gray-logo.png', destination_peer)

    # Now invite all mods as Admins
    await add_admins(client, destination_peer)

    # Forward all our seeded topic messages and pin what we can before getting throttled
    for topic_name, info in TOPIC_FORWARD_MAP.items():
        await forward_and_try_pinning_msgs(client, info, topic_name, new_group, source_peer, destination_peer)

    await client.disconnect()
    logging.info(f"All done! New Group at: https://web.telegram.org/a/#-100{new_group.id}_1")

# -------------------------------------------------------------------
# 5) Helper Functions
# -------------------------------------------------------------------
async def safe_telethon_call(client, request):
    """
    Executes a Telethon request, catching FloodWaitError.
    If a FloodWaitError occurs and the wait is 60 seconds or less,
    sleep that long and retry. If it's more than 5 minutes, log
    a warning and return None (skipping the request).
    """
    while True:
        try:
            return await client(request)
        except FloodWaitError as e:
            if e.seconds > 60*5:
                logging.warning(
                    f"FloodWaitError: {e.seconds}s is longer than 5 mins, skipping this request."
                )
                return None
            else:
                logging.warning(f"FloodWaitError: must wait {e.seconds}s before retry.")
                await asyncio.sleep(e.seconds)


async def rename_and_lock_general(client, new_group):
    # (3) Rename the auto-created "General" topic to "Welcome" and lock it
    #     We find it by listing all current topics and searching for "General"
    topics_result = await client(GetForumTopicsRequest(
        channel=new_group,
        offset_date=0,
        offset_id=0,
        offset_topic=0,
        limit=10
    ))
    general_topic = None
    for t in topics_result.topics:
        if t.title == "General":
            general_topic = t
            break

    if general_topic:
        logging.info(f"Renaming 'General' topic (ID={general_topic.id}) to 'Welcome'...")

        # 3a) Rename the topic
        rename_topic_req = EditForumTopicRequest(
            channel=new_group,
            topic_id=general_topic.id,
            title="Welcome"
        )
        await safe_telethon_call(client, rename_topic_req)
        await asyncio.sleep(1.0)

        # 3b) Close (lock) the topic in a separate request
        logging.info(f"Closing (locking) the renamed 'Welcome' topic...")
        close_topic_req = EditForumTopicRequest(
            channel=new_group,
            topic_id=general_topic.id,
            closed=True
        )
        await safe_telethon_call(client, close_topic_req)
        await asyncio.sleep(1.0)

        logging.info("Successfully renamed and closed the default 'General' topic.")
    else:
        logging.warning("No 'General' topic found to rename/close.")


async def forward_and_try_pinning_msgs(client, info, topic_name, new_group, source_peer, destination_peer):
    message_ids = info["messages"]
    icon_color = info.get("icon_color")
    icon_emoji_id = info.get("icon_emoji_id")

    create_topic_req = CreateForumTopicRequest(
        channel=new_group, 
        title=topic_name,
        icon_color=icon_color, 
        icon_emoji_id=icon_emoji_id
    )
    await safe_telethon_call(client, create_topic_req)
    await asyncio.sleep(1.0)

    logging.info(f"Created topic: {topic_name}")

    # Find the newly created topic
    topics_result = await client(GetForumTopicsRequest(
        channel=new_group,
        offset_date=0,
        offset_id=0,
        offset_topic=0,
        limit=len(TOPIC_FORWARD_MAP)+5
    ))

    new_topic = None
    for t in topics_result.topics:
        if t.title == topic_name:
            new_topic = t
            break

    if not new_topic:
        logging.warning("Topic not found, cannot forward.")
        return

    logging.info(f"Found topic '{topic_name}' with topic_id = {new_topic.id}.")

    # anchor message for the topic:
    top_msg_id = new_topic.top_message  

    # Forward the specified messages into this topic
    for source_msg_id in message_ids:
        forward_req = ForwardMessagesRequest(
            from_peer=source_peer,
            id=[int(source_msg_id)],
            to_peer=destination_peer,
            top_msg_id=top_msg_id,  
            silent=True,
            drop_author=False
        )
        fwd_result = await safe_telethon_call(client, forward_req)
        await asyncio.sleep(1.0)

        if not fwd_result:
            logging.warning(f"Forward request for msg #{source_msg_id} returned None (probably flood limit). Skipping.")
            continue

        new_msg_id = None
        for u in fwd_result.updates:
            if isinstance(u, UpdateNewChannelMessage):
                new_msg_id = u.message.id
                break

        logging.info(f"Forwarded message #{source_msg_id} (destination msg ID: {new_msg_id})")

        # Optionally pin the new message
        if new_msg_id:
            pin_request = UpdatePinnedMessageRequest(
                peer=destination_peer,
                id=new_msg_id,
                silent=True
            )
            await safe_telethon_call(client, pin_request)
            await asyncio.sleep(1.0)
        else:
            logging.warning("No new message ID found in the forward result. Could not pin.")


async def set_logo(client, pic_path, destination_peer):
    # 1) Upload the photo file to Telegram
    uploaded_photo = await client.upload_file(pic_path)

    # 2) Call EditPhotoRequest to set the group's photo
    add_photo_req = EditPhotoRequest(
        channel=destination_peer,
        photo=InputChatUploadedPhoto(uploaded_photo)
    )
    await safe_telethon_call(client, add_photo_req)
    logging.info(f"Set group logo from: {pic_path}")


async def add_admins(client, new_group_peer):
    for user_id in USERS_TO_ADD:
        # 1) Get the user entity
        try:
            user_entity = await client.get_entity(user_id)
        except ValueError:
            logging.warning(f"Could not find user: {user_id}. Skipping.")
            continue

        # 2) Invite the user to the channel (if they aren't already in it)
        try:
            await client(InviteToChannelRequest(
                channel=new_group_peer,
                users=[user_entity]
            ))
            logging.info(f"Invited {user_id} to the new group.")
        except UserAlreadyParticipantError:
            logging.info(f"{user_id} is already in the group.")
        except FloodWaitError as fw:
            logging.warning(f"FloodWaitError: must wait {fw.seconds}s.")
            await asyncio.sleep(fw.seconds)
        except Exception as e:
            logging.error(f"Failed to invite {user_id}: {e}")
            continue

        # 3) Promote the user to admin
        try:
            await client(EditAdminRequest(
                channel=new_group_peer,
                user_id=user_entity,
                admin_rights=ADMIN_RIGHTS,
                rank="Admin"  # or "Moderator", "Co-Owner", etc.
            ))
            logging.info(f"Promoted {user_id} to admin.")
        except FloodWaitError as fw:
            logging.warning(f"FloodWaitError while promoting: {fw.seconds}s wait.")
            await asyncio.sleep(fw.seconds)
        except Exception as e:
            logging.error(f"Failed to promote {user_id} to admin: {e}")
            # Possibly continue or break

# -------------------------------------------------------------------
# 6) RUN
# -------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
