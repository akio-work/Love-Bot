import sqlite3

DB_FILENAME = "love_bot.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILENAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS couples (
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            wed_date TEXT NOT NULL,
            PRIMARY KEY (user1_id, user2_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'uk',
            status TEXT DEFAULT 'Вільний(а)'
        )
    """)
    conn.commit()
    return conn
