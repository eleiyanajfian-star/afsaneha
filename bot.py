import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import (
    init_db, add_or_update_user, increment_message_count,
    save_message, get_user_by_admin_msg, get_stats, get_all_users
)

# ============ تنظیمات ============
TOKEN = "8840828687:AAFVSbLqr_fgwZxYSBkwmrOOUvqjuktPOHE"
ADMIN_ID = 8854675840

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============ /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username or "", user.full_name)
    keyboard = [[InlineKeyboardButton("📩 ارسال پیام به پشتیبانی", callback_data="contact_support")]]
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n\n"
        "به ربات پشتیبانی خوش آمدید.\n"
        "برای ارتباط با پشتیبانی روی دکمه زیر بزنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============ دکمه پشتیبانی ============
async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['waiting_for_message'] = True
    await query.edit_message_text(
        "✍️ لطفاً پیام خود را بنویسید.\n"
        "می‌توانید متن، عکس، فایل، ویس یا ویدیو بفرستید."
    )


# ============ استخراج محتوا ============
def extract_content(message):
    if message.text:
        return "text", message.text
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.document:
        return "document", message.document.file_id
    if message.voice:
        return "voice", message.voice.file_id
    if message.video:
        return "video", message.video.file_id
    if message.audio:
        return "audio", message.audio.file_id
    if message.sticker:
        return "sticker", message.sticker.file_id
    return None, None


# ============ ارسال محتوا ============
async def send_content(bot, chat_id, content_type, content, caption=None, reply_to=None):
    kwargs = {"chat_id": chat_id}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to

    if content_type == "text":
        await bot.send_message(text=content, **kwargs)
    elif content_type == "photo":
        await bot.send_photo(photo=content, caption=caption, **kwargs)
    elif content_type == "document":
        await bot.send_document(document=content, caption=caption, **kwargs)
    elif content_type == "voice":
        await bot.send_voice(voice=content, caption=caption, **kwargs)
    elif content_type == "video":
        await bot.send_video(video=content, caption=caption, **kwargs)
    elif content_type == "audio":
        await bot.send_audio(audio=content, caption=caption, **kwargs)
    elif content_type == "sticker":
        await bot.send_sticker(sticker=content, **kwargs)


# ============ پیام کاربر ============
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    add_or_update_user(user.id, user.username or "", user.full_name)

    if not context.user_data.get('waiting_for_message'):
        await message.reply_text("برای ارسال پیام به پشتیبانی، ابتدا /start رو بزن.")
        return

    content_type, content = extract_content(message)
    if not content_type:
        await message.reply_text("❌ این نوع پیام پشتیبانی نمی‌شود.")
        return

    header = (
        f"📩 **پیام جدید**\n\n"
        f"👤 {user.full_name}\n"
        f"🆔 `{user.id}`\n"
        f"🔗 @{user.username if user.username else 'ندارد'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    try:
        header_msg = await context.bot.send_message(
            chat_id=ADMIN_ID, text=header, parse_mode='Markdown'
        )
        admin_msg = await send_content(
            context.bot, ADMIN_ID, content_type, content,
            caption=message.caption, reply_to=header_msg.message_id
        )
        save_message(user.id, admin_msg.message_id, message.message_id,
                     content_type, str(content), is_from_admin=0)
        increment_message_count(user.id)
        await message.reply_text("✅ پیام شما ارسال شد.\nبه‌زودی پاسخ داده می‌شود.")
        context.user_data['waiting_for_message'] = False
    except Exception as e:
        logger.error(f"خطا: {e}")
        await message.reply_text("❌ خطا در ارسال پیام.")


# ============ پاسخ ادمین ============
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("⚠️ روی پیام کاربر **ریپلای** بزن.", parse_mode='Markdown')
        return

    replied_id = message.reply_to_message.message_id
    user_id = get_user_by_admin_msg(replied_id)

    if not user_id:
        await message.reply_text("❌ کاربر پیدا نشد. روی پیام اصلی کاربر ریپلای بزن.")
        return

    content_type, content = extract_content(message)
    if not content_type:
        await message.reply_text("❌ این نوع پیام پشتیبانی نمی‌شود.")
        return

    try:
        await send_content(
            context.bot, user_id, content_type, content,
            caption=f"📬 **پاسخ پشتیبانی:**\n\n{message.caption or ''}"
        )
        save_message(user_id, message.message_id, 0, content_type,
                     str(content), is_from_admin=1)
        await message.reply_text("✅ پاسخ ارسال شد.")
    except Exception as e:
        logger.error(f"خطا: {e}")
        await message.reply_text(f"❌ خطا: {e}")


# ============ پنل ادمین ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    stats = get_stats()
    text = (
        f"📊 **پنل مدیریت**\n\n"
        f"👥 کاربران: `{stats['total_users']}`\n"
        f"🟢 فعال امروز: `{stats['active_today']}`\n"
        f"📩 پیام‌های کاربران: `{stats['total_user_msgs']}`\n"
        f"📤 پاسخ‌های شما: `{stats['total_admin_msgs']}`\n\n"
        f"دستورات:\n"
        f"/stats - آمار\n"
        f"/users - لیست کاربران\n"
        f"/broadcast - پیام همگانی\n"
        f"/cancel - لغو"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = get_all_users(limit=30)
    if not users:
        await update.message.reply_text("هنوز کاربری ثبت نشده.")
        return
    text = "👥 **آخرین کاربران:**\n\n"
    for uid, name, username, count, last in users:
        text += f"• {name} (`{uid}`)\n  📩 {count} پیام | @{username or '—'}\n\n"
    await update.message.reply_text(text[:4000], parse_mode='Markdown')


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data['broadcast_mode'] = True
    await update.message.reply_text("📢 پیام همگانی رو بفرست.\nبرای لغو /cancel رو بزن.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ لغو شد.")


async def do_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('broadcast_mode'):
        return
    users = get_all_users(limit=10000)
    content_type, content = extract_content(update.message)
    if not content_type:
        return
    success, failed = 0, 0
    for uid, *_ in users:
        try:
            await send_content(context.bot, uid, content_type, content, caption=update.message.caption)
            success += 1
        except:
            failed += 1
    await update.message.reply_text(f"✅ ارسال شد: {success}\n❌ ناموفق: {failed}")
    context.user_data['broadcast_mode'] = False


# ============ روتر ============
async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        if context.user_data.get('broadcast_mode'):
            await do_broadcast(update, context)
        else:
            await handle_admin_reply(update, context)
    else:
        await handle_user_message(update, context)


# ============ main ============
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_panel))
    app.add_handler(CommandHandler("users", users_list))
    app.add_handler(CommandHandler("broadcast", broadcast_start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(contact_support, pattern="^contact_support$"))
    app.add_handler(MessageHandler(
        ~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.Document.ALL |
                             filters.VOICE | filters.VIDEO | filters.AUDIO | filters.Sticker.ALL),
        route_message
    ))
    print("🤖 ربات روشن شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()