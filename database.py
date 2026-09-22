import sqlite3, os
from datetime import datetime

# دیتابیس توی مسیر /app ساخته میشه که قطعاً وجود داره
DB_NAME = "/app/support_bot.db"
print(f"📁 مسیر دیتابیس: {DB_NAME}")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        first_seen TEXT,
        last_seen TEXT,
        message_count INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        admin_msg_id INTEGER,
        user_msg_id INTEGER,
        content_type TEXT,
        content TEXT,
        is_from_admin INTEGER DEFAULT 0,
        created_at TEXT)""")
    conn.commit()
    conn.close()
    print("✅ دیتابیس آماده شد")


def add_or_update_user(user_id, username, full_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if c.fetchone():
        c.execute("UPDATE users SET username=?, full_name=?, last_seen=? WHERE user_id=?",
                  (username, full_name, now, user_id))
    else:
        c.execute("INSERT INTO users (user_id, username, full_name, first_seen, last_seen) VALUES (?,?,?,?,?)",
                  (user_id, username, full_name, now, now))
    conn.commit()
    conn.close()


def increment_message_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_message(user_id, admin_msg_id, user_msg_id, content_type, content, is_from_admin=0):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""INSERT INTO messages (user_id, admin_msg_id, user_msg_id, content_type, content, is_from_admin, created_at)
                    VALUES (?,?,?,?,?,?,?)""",
                 (user_id, admin_msg_id, user_msg_id, content_type, content, is_from_admin, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_user_by_admin_msg(admin_msg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM messages WHERE admin_msg_id = ?", (admin_msg_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages WHERE is_from_admin = 0")
    total_user_msgs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages WHERE is_from_admin = 1")
    total_admin_msgs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE last_seen > datetime('now', '-1 day')")
    active_today = c.fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "total_user_msgs": total_user_msgs,
        "total_admin_msgs": total_admin_msgs,
        "active_today": active_today
    }


def get_all_users(limit=50):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, username, message_count, last_seen FROM users ORDER BY last_seen DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
