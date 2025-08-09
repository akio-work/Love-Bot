import sqlite3
from datetime import datetime

def get_db_connection(chat_id: int):
    db_name = f"db_group_{chat_id}.db"
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS couples (
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        wed_date TEXT NOT NULL,
        PRIMARY KEY (user1_id, user2_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'uk'
    )
    """)

    conn.commit()
    return conn

def insert_couple(conn, user1_id: int, user2_id: int):
    c = conn.cursor()
    now_str = datetime.now().isoformat()
    # Вставляємо пару (впорядкуємо id для унікальності)
    low_id, high_id = min(user1_id, user2_id), max(user1_id, user2_id)
    c.execute('INSERT OR IGNORE INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (low_id, high_id, now_str))
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user1_id,))
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user2_id,))
    conn.commit()

def get_couple_by_user(conn, user_id: int):
    c = conn.cursor()
    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    return c.fetchone()

def delete_couple(conn, user1_id: int, user2_id: int):
    c = conn.cursor()
    low_id, high_id = min(user1_id, user2_id), max(user1_id, user2_id)
    c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (low_id, high_id))
    conn.commit()

def get_all_couples(conn):
    c = conn.cursor()
    c.execute('SELECT user1_id, user2_id, wed_date FROM couples')
    return c.fetchall()
