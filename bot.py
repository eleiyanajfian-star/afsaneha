import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import (
    init_db, add_or_update_user, increment_message_count,
    save_message, get_user_by_admin_msg
)

TOKEN = "8840828687:AAFVSbLqr_fgwZxYSBkwmrOOUvqjuktPOHE"
ADMIN_ID = 8854675840

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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


async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['waiting_for_message'] = True
    await query.edit_message_text(
        "✍️ لطفاً پیام خود را بنویسید.\n"
        "می‌توانید متن، عکس، فایل، ویس یا ویدیو بفرستید."
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    add_or_update_user(user.id, user.username or "", user.full_name)

    if not context.user_data.get('waiting_for_message'):
        await message.reply_text("برای ارسال پیام به پشتیبانی، ابتدا /start رو بزن.")
        return

    # فقط متن
    if message.text:
        content_type = "text"
        content = message.text
    elif message.photo:
        content_type = "photo"
        content = message.photo[-1].file_id
    elif message.document:
        content_type = "document"
        content = message.document.file_id
    elif message.voice:
        content_type = "voice"
        content = message.voice.file_id
    elif message.video:
        content_type = "video"
        content = message.video.file_id
    else:
        await message.reply_text("❌ این نوع پیام پشتیبانی نمی‌شود.")
        return

    header = (
        f"📩 پیام جدید\n\n"
        f"👤 {user.full_name}\n"
        f"🆔 {user.id}\n"
        f"🔗 @{user.username if user.username else 'ندارد'}"
    )

    try:
        # ارسال هدر (بدون Markdown)
        header_msg = await context.bot.send_message(chat_id=ADMIN_ID, text=header)

        # ارسال محتوا
        if content_type == "text":
            admin_msg = await context.bot.send_message(chat_id=ADMIN_ID, text=content,
                                                       reply_to_message_id=header_msg.message_id)
        elif content_type == "photo":
            admin_msg = await context.bot.send_photo(chat_id=ADMIN_ID, photo=content,
                                                      caption=message.caption or "",
                                                      reply_to_message_id=header_msg.message_id)
        elif content_type == "document":
            admin_msg = await context.bot.send_document(chat_id=ADMIN_ID, document=content,
                                                         caption=message.caption or "",
                                                         reply_to_message_id=header_msg.message_id)
        elif content_type == "voice":
            admin_msg = await context.bot.send_voice(chat_id=ADMIN_ID, voice=content,
                                                      reply_to_message_id=header_msg.message_id)
        elif content_type == "video":
            admin_msg = await context.bot.send_video(chat_id=ADMIN_ID, video=content,
                                                      caption=message.caption or "",
                                                      reply_to_message_id=header_msg.message_id)

        save_message(user.id, admin_msg.message_id, message.message_id,
                     content_type, str(content), is_from_admin=0)
        increment_message_count(user.id)

        await message.reply_text("✅ پیام شما ارسال شد.\nبه‌زودی پاسخ داده می‌شود.")
        context.user_data['waiting_for_message'] = False

    except Exception as e:
        logger.error(f"خطا در handle_user_message: {e}", exc_info=True)
        await message.reply_text(f"❌ خطا: {e}")


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message.reply_to_message:
        await message.reply_text("⚠️ روی پیام کاربر ریپلای بزن.")
        return

    replied_id = message.reply_to_message.message_id
    user_id = get_user_by_admin_msg(replied_id)

    if not user_id:
        await message.reply_text("❌ کاربر پیدا نشد. روی پیام اصلی کاربر ریپلای بزن.")
        return

    try:
        if message.text:
            await context.bot.send_message(chat_id=user_id, text=f"📬 پاسخ پشتیبانی:\n\n{message.text}")
        elif message.photo:
            await context.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id,
                                          caption=f"📬 پاسخ پشتیبانی:\n\n{message.caption or ''}")
        elif message.document:
            await context.bot.send_document(chat_id=user_id, document=message.document.file_id,
                                             caption=f"📬 پاسخ پشتیبانی:\n\n{message.caption or ''}")
        else:
            await message.reply_text("❌ این نوع پیام پشتیبانی نمی‌شود.")
            return

        save_message(user_id, message.message_id, 0, "text", str(message.text or ""), is_from_admin=1)
        await message.reply_text("✅ پاسخ ارسال شد.")

    except Exception as e:
        logger.error(f"خطا در handle_admin_reply: {e}", exc_info=True)
        await message.reply_text(f"❌ خطا: {e}")


async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        await handle_admin_reply(update, context)
    else:
        await handle_user_message(update, context)


def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(contact_support, pattern="^contact_support$"))
    app.add_handler(MessageHandler(
        ~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.Document.ALL |
                             filters.VOICE | filters.VIDEO),
        route_message
    ))

    print("🤖 ربات روشن شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
