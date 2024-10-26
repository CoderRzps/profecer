import os, re, json, base64, logging, random, asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Script import script
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, START_MESSAGE, FORCE_SUB_TEXT, SUPPORT_CHAT
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp
from database.connections_mdb import active_connection

logger = logging.getLogger(__name__)
BATCH_FILES = {}

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [[           
            InlineKeyboardButton('📢 Updates 📢', url=f'https://t.me/{SUPPORT_CHAT}')
            ],[
            InlineKeyboardButton('ℹ️ Help ℹ️', url=f"https://t.me/{temp.U_NAME}?start=help")
        ]]
        await message.reply(
            START_MESSAGE.format(
                user=message.from_user.mention if message.from_user else message.chat.title,
                bot=client.mention
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        await asyncio.sleep(2)
        
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(
                a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total,
                f=client.mention, e="Unknown"
            ))
            await db.add_chat(message.chat.id, message.chat.title, message.chat.username)
        return 

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(
            LOG_CHANNEL,
            script.LOG_TEXT_P.format(
                message.from_user.id, message.from_user.mention, message.from_user.username, temp.U_NAME
            )
        )
    
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton("Search 🔎", switch_inline_query_current_chat=''), 
            InlineKeyboardButton("Channel 🔈", url="https://t.me/mkn_bots_updates")
            ],[      
            InlineKeyboardButton("Help 🕸️", callback_data="help"),
            InlineKeyboardButton("About ✨", callback_data="about")
        ]]
        m = await message.reply_sticker("CAACAgUAAxkBAAEBvlVk7YKnYxIHVnKW2PUwoibIR2ygGAACBAADwSQxMYnlHW4Ls8gQHgQ") 
        await asyncio.sleep(2)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=START_MESSAGE.format(user=message.from_user.mention, bot=client.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        return await m.delete()
    
    if AUTH_CHANNEL and not await is_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("MAKE SURE BOT IS ADMIN IN FORCESUB CHANNEL")
            return
        btn = [[InlineKeyboardButton("Join My Channel ✨", url=invite_link.invite_link)]]
        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("⟳ Try Again", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("⟳ Try Again", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        
        try:
            return await client.send_message(
                chat_id=message.from_user.id, 
                text=FORCE_SUB_TEXT, 
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.DEFAULT
            )
        except Exception as e:
            print(f"Force Sub Text Error\n{e}")
            return await client.send_message(
                chat_id=message.from_user.id, 
                text=script.FORCE_SUB_TEXT,
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.DEFAULT
            )
    
    # Handle batch files
    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("PLEASE WAIT......")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(
                        mention=message.from_user.mention,
                        file_name= '' if title is None else title,
                        file_size='' if size is None else size,
                        file_caption='' if f_caption is None else f_caption
                    )
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id, 
                    file_id=msg.get("file_id"), 
                    caption=f_caption, 
                    protect_content=msg.get('protect', False)
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await client.send_cached_media(
                    chat_id=message.from_user.id, 
                    file_id=msg.get("file_id"), 
                    caption=f_caption, 
                    protect_content=msg.get('protect', False)
                )
            await asyncio.sleep(1) 
        return await sts.delete()

    await message.reply("INVALID FILE")

# Settings Command
@Client.on_message(filters.command("settings") & filters.user(ADMINS))
async def settings(client, message):
    grp_id = message.chat.id
    settings = await get_settings(grp_id)

    if settings:
        buttons = [
            [
                InlineKeyboardButton(f"ʙᴏᴛ ᴘᴍ: {'ᴏɴ' if settings['botpm'] else 'ᴏꜰꜰ'}", f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
            ],
            [
                InlineKeyboardButton(f"ʙᴜᴛᴛᴏɴ: {'ᴏɴ' if settings['button'] else 'ᴏꜰꜰ'}", f'setgs#button#{settings["button"]}#{str(grp_id)}')
            ],
            [
                InlineKeyboardButton(f"ʀᴇꜱᴛʀɪᴄᴛ ᴄᴏɴᴛᴇɴᴛ: {'ᴏɴ' if settings['restrict'] else 'ᴏꜰꜰ'}", f'setgs#restrict#{settings["restrict"]}#{str(grp_id)}')
            ],
            [
                InlineKeyboardButton(f"ᴀᴅᴅ ʜᴏʟᴅᴇʀ: {'ᴏɴ' if settings['add_holder'] else 'ᴏꜰ꜀'}", f'setgs#add_holder#{settings["add_holder"]}#{str(grp_id)}')
            ],
            [
                InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data='settings_back')
            ]
        ]
        await message.reply_text("Cʜᴏᴏsᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text("Nᴏ sᴇᴛᴛɪɴɢs ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.")

# Update Settings via Callback Query
@Client.on_callback_query(filters.regex(r'^setgs'))
async def update_settings(bot, callback):
    data = callback.data.split('#')
    setting = data[1]
    value = data[2] == 'True'  # Convert string to boolean
    grp_id = int(data[3])

    current_settings = await get_settings(grp_id)
    if current_settings is None:
        return await callback.answer("Nᴏ sᴇᴛᴛɪɴɢs ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.")

    # Toggle the setting based on callback data
    if setting == 'button':
        current_settings['button'] = not current_settings['button']
    elif setting == 'botpm':
        current_settings['botpm'] = not current_settings['botpm']
    elif setting == 'restrict':
        current_settings['restrict'] = not current_settings['restrict']
    elif setting == 'add_holder':
        current_settings['add_holder'] = not current_settings['add_holder']

    await save_group_settings(grp_id, current_settings)
    await callback.answer("Sᴇᴛᴛɪɴɢs Uᴘᴅᴀᴛᴇᴅ!", show_alert=True)

    # Refresh settings display
    await settings(bot, callback.message)

# Back button for settings
@Client.on_callback_query(filters.regex(r'^settings_back'))
async def settings_back(bot, callback):
    await callback.message.delete()
    await settings(bot, callback.message)

# Save Template Command
@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Cʜᴇᴄᴋɪɴɢ Tᴇᴍᴘʟᴀᴛᴇ")
    userid = message.from_user.id if message.from_user else None
    if not userid: 
        return await message.reply(f"Yᴏᴜ Aʀᴇ Aɴᴏɴʏᴍᴏᴜs Aᴅᴍɪɴ. Usᴇ /connect {message.chat.id} Iɴ PM")
    
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                return await message.reply_text("Mᴀᴋᴇ Sᴜʀᴇ I'ᴍ Pʀᴇsᴇɴᴛ Iɴ Yᴏᴜʀ Gʀᴏᴜᴘ!", quote=True)
        else:
            return await message.reply_text("I'ᴍ Nᴏᴛ Cᴏɴɴᴇᴄᴛᴇᴅ Tᴏ Aɴʏ Gʀᴏᴜᴘs!", quote=True)
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else: 
        return
    
    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status != enums.ChatMemberStatus.ADMINISTRATOR
        and st.status != enums.ChatMemberStatus.OWNER
        and str(userid) not in ADMINS
    ): return
    
    if len(message.command) < 2: 
        return await sts.edit("No Iɴᴩᴜᴛ!!")
    
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Sᴜᴄᴄᴇssғᴜʟʟʏ Cʜᴀɴɢᴇᴅ Tᴇᴍᴘʟᴀᴛᴇ ғᴏʀ {title} Tᴏ\n\n{template}")

# Get Template Command
@Client.on_message(filters.command('get_template'))
async def get_template(client, message):
    sts = await message.reply("Cʜᴇᴄᴋɪɴɢ Tᴇᴍᴘʟᴀᴛᴇ")
    userid = message.from_user.id if message.from_user else None
    if not userid: 
        return await message.reply(f"Yᴏᴜ Aʀᴇ Aɴᴏɴʏᴍᴏᴜs Aᴅᴍɪɴ. Usᴇ /connect {message.chat.id} Iɴ PM")
    
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                return await message.reply_text("Mᴀᴋᴇ Sᴜʀᴇ I'ᴍ Pʀᴇsᴇɴᴛ Iɴ Yᴏᴜʀ Gʀᴏᴜᴘ!", quote=True)
        else:
            return await message.reply_text("I'ᴍ Nᴏᴛ Cᴏɴɴᴇᴄᴛᴇᴅ Tᴏ Aɴʏ Gʀᴏᴜᴘs!", quote=True)
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else: 
        return
    
    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status != enums.ChatMemberStatus.ADMINISTRATOR
        and st.status != enums.ChatMemberStatus.OWNER
        and str(userid) not in ADMINS
    ): return
    
    settings = await get_settings(grp_id)
    template = settings.get('template', 'No Template Set')
    await sts.edit(f"Cᴜʀʀᴇɴᴛ Tᴇᴍᴘʟᴀᴛᴇ ғᴏʀ {title} Iꜱ\n\n{template}")
