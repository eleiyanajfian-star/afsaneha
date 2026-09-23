import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler, ContextTypes, filters
)
from database import (
    init_db, add_or_update_user, increment_message_count,
    save_message, get_user_by_admin_msg, get_stats, get_all_users,
    ban_user, unban_user, is_banned, log_channel_join, get_channel_stats
)

# ============ تنظیمات ============
TOKEN = "8840828687:AAFVSbLqr_fgwZxYSBkwmrOOUvqjuktPOHE"
ADMIN_ID = 8854675840
CHANNEL_ID = -1001234567890  # ← آیدی عددی کانال خود را اینجا بگذارید

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============ /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username or "", user.full_name)

    if is_banned(user.id):
        await update.message.reply_text("❌ شما از ربات مسدود شده‌اید.")
        return

    # دکمه شیشه‌ای برای پشتیبانی
    keyboard = [[InlineKeyboardButton("📩 ارسال پیام به پشتیبانی", callback_data="contact_support")]]

    # دکمه کیبورد برای دریافت شماره
    contact_button = KeyboardButton("📱 ارسال شماره تلفن", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n\n"
        "به ربات پشتیبانی خوش آمدید.\n"
        "لطفاً برای شروع، شماره تلفن خود را با دکمه زیر ارسال کنید:",
        reply_markup=reply_markup
    )
    await update.message.reply_text(
        "برای ارتباط با پشتیبانی روی دکمه زیر بزنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============ دریافت شماره تلفن ============
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    if contact and contact.user_id == user.id:
        # ذخیره شماره در دیتابیس (نیاز به اضافه کردن تابع به database.py)
        from database import save_user_phone
        save_user_phone(user.id, contact.phone_number)
        await update.message.reply_text(
            "✅ شماره تلفن شما ثبت شد.\n"
            "حالا می‌توانید پیام خود را بفرستید.",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)  # حذف کیبورد
        )
        context.user_data['phone_verified'] = True
    else:
        await update.message.reply_text("❌ لطفاً از دکمه ارسال شماره استفاده کنید.")


# ============ دکمه پشتیبانی ============
async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if is_banned(query.from_user.id):
        await query.edit_message_text("❌ شما از ربات مسدود شده‌اید.")
        return

    context.user_data['waiting_for_message'] = True
    await query.edit_message_text(
        "✍️ لطفاً پیام خود را بنویسید.\n"
        "می‌توانید متن، عکس، فایل، ویس یا ویدیو بفرستید."
    )


# ============ پیام کاربر ============
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    if is_banned(user.id):
        await message.reply_text("❌ شما از ربات مسدود شده‌اید.")
        return

    add_or_update_user(user.id, user.username or "", user.full_name)

    if not context.user_data.get('waiting_for_message'):
        await message.reply_text("برای ارسال پیام به پشتیبانی، ابتدا /start رو بزن.")
        return

    # استخراج محتوا
    if message.text:
        content_type, content = "text", message.text
    elif message.photo:
        content_type, content = "photo", message.photo[-1].file_id
    elif message.document:
        content_type, content = "document", message.document.file_id
    elif message.voice:
        content_type, content = "voice", message.voice.file_id
    elif message.video:
        content_type, content = "video", message.video.file_id
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
        header_msg = await context.bot.send_message(chat_id=ADMIN_ID, text=header)

        if content_type == "text":
            admin_msg = await context.bot.send_message(
                chat_id=ADMIN_ID, text=content,
                reply_to_message_id=header_msg.message_id
            )
        elif content_type == "photo":
            admin_msg = await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=content, caption=message.caption or "",
                reply_to_message_id=header_msg.message_id
            )
        elif content_type == "document":
            admin_msg = await context.bot.send_document(
                chat_id=ADMIN_ID, document=content, caption=message.caption or "",
                reply_to_message_id=header_msg.message_id
            )
        elif content_type == "voice":
            admin_msg = await context.bot.send_voice(
                chat_id=ADMIN_ID, voice=content,
                reply_to_message_id=header_msg.message_id
            )
        elif content_type == "video":
            admin_msg = await context.bot.send_video(
                chat_id=ADMIN_ID, video=content, caption=message.caption or "",
                reply_to_message_id=header_msg.message_id
            )

        save_message(user.id, admin_msg.message_id, message.message_id,
                     content_type, str(content), is_from_admin=0)
        increment_message_count(user.id)

        await message.reply_text("✅ پیام شما ارسال شد.\nبه‌زودی پاسخ داده می‌شود.")
        context.user_data['waiting_for_message'] = False

    except Exception as e:
        logger.error(f"خطا در handle_user_message: {e}", exc_info=True)
        await message.reply_text(f"❌ خطا: {e}")


# ============ پاسخ ادمین ============
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


# ============ دستورات ادمین ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    stats = get_stats()
    channel_stats = get_channel_stats()
    text = (
        f"📊 پنل مدیریت\n\n"
        f"👥 کاربران ربات: {stats['total_users']}\n"
        f"🟢 فعال امروز: {stats['active_today']}\n"
        f"📩 پیام‌های کاربران: {stats['total_user_msgs']}\n"
        f"📤 پاسخ‌های شما: {stats['total_admin_msgs']}\n\n"
        f"📢 آمار کانال:\n"
        f"👥 ورودهای امروز: {channel_stats['today_joins']}\n"
        f"🚪 خروج‌های امروز: {channel_stats['today_leaves']}\n"
        f"👥 کل اعضای ثبت‌شده: {channel_stats['total_members']}\n\n"
        f"دستورات:\n"
        f"/stats - آمار\n"
        f"/users - لیست کاربران\n"
        f"/broadcast - پیام همگانی\n"
        f"/ban [user_id] - بلاک کاربر\n"
        f"/unban [user_id] - آنبلاک کاربر\n"
        f"/cancel - لغو"
    )
    await update.message.reply_text(text)


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /ban [user_id]")
        return
    try:
        user_id = int(context.args[0])
        ban_user(user_id)
        await update.message.reply_text(f"✅ کاربر {user_id} بلاک شد.")
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /unban [user_id]")
        return
    try:
        user_id = int(context.args[0])
        unban_user(user_id)
        await update.message.reply_text(f"✅ کاربر {user_id} آنبلاک شد.")
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر.")


# ============ رهگیری عضویت در کانال ============
async def track_channel_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رهگیری ورود/خروج اعضای کانال"""
    result = update.chat_member
    if result is None:
        return

    # چک کردن اینکه مربوط به کانال ماست
    if result.chat.id != CHANNEL_ID:
        return

    # تشخیص تغییر وضعیت
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    was_member = old_status in ['member', 'administrator', 'creator']
    is_member = new_status in ['member', 'administrator', 'creator']

    user = result.new_chat_member.user
    full_name = user.full_name

    if not was_member and is_member:
        # کاربر جدید وارد شد
        log_channel_join(user.id, full_name, "join")
        logger.info(f"✅ کاربر جدید در کانال: {full_name} ({user.id})")

    elif was_member and not is_member:
        # کاربر خارج شد
        log_channel_join(user.id, full_name, "leave")
        logger.info(f"🚪 کاربر از کانال خارج شد: {full_name} ({user.id})")


# ============ روتر پیام‌ها ============
async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # اگه شماره فرستاده شد
    if update.message.contact:
        await handle_contact(update, context)
        return

    if user.id == ADMIN_ID:
        await handle_admin_reply(update, context)
    else:
        await handle_user_message(update, context)


# ============ main ============
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_panel))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))

    # کالبک دکمه‌ها
    app.add_handler(CallbackQueryHandler(contact_support, pattern="^contact_support$"))

    # رهگیری عضویت کانال (مهم!)
    app.add_handler(ChatMemberHandler(track_channel_members, ChatMemberHandler.CHAT_MEMBER))

    # پیام‌های متنی
    app.add_handler(MessageHandler(
        ~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.Document.ALL |
                             filters.VOICE | filters.VIDEO | filters.CONTACT),
        route_message
    ))

    print("🤖 ربات روشن شد...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()
