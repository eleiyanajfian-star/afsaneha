# ============ توابع جدید ============

def save_user_phone(user_id, phone_number):
    """ذخیره شماره تلفن کاربر"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET phone_number = ? WHERE user_id = ?", (phone_number, user_id))
    conn.commit()
    conn.close()


def ban_user(user_id):
    """بلاک کردن کاربر"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id):
    """آنبلاک کردن کاربر"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_banned(user_id):
    """چک کردن بلاک بودن کاربر"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1


def log_channel_join(user_id, full_name, event_type):
    """ثبت ورود/خروج اعضای کانال"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""INSERT INTO channel_logs (user_id, full_name, event_type, created_at)
                    VALUES (?, ?, ?, ?)""",
                 (user_id, full_name, event_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_channel_stats():
    """آمار کانال"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM channel_logs WHERE event_type='join' AND date(created_at)=date('now')")
    today_joins = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM channel_logs WHERE event_type='leave' AND date(created_at)=date('now')")
    today_leaves = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT user_id) FROM channel_logs WHERE event_type='join'")
    total_members = c.fetchone()[0]

    conn.close()
    return {
        "today_joins": today_joins,
        "today_leaves": today_leaves,
        "total_members": total_members
    }
