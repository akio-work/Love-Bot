import sqlite3
from contextlib import closing

DB_PATH = "lovebot.db"

def get_db(chat_id=None):
    # chat_id поки не використовуємо, бо база одна
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    create_tables(conn)
    return conn

def create_tables(conn):
    with closing(conn.cursor()) as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'uk',
            status TEXT DEFAULT 'Вільний(а)'
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS couples (
            user1_id INTEGER,
            user2_id INTEGER,
            wed_date TEXT,
            PRIMARY KEY (user1_id, user2_id),
            FOREIGN KEY (user1_id) REFERENCES users(user_id),
            FOREIGN KEY (user2_id) REFERENCES users(user_id)
        )
        """)
    conn.commit()

def get_lang_status(c, user_id):
    c.execute("SELECT lang, status FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        return row[0], row[1]
    return "uk", "Вільний(а)"
