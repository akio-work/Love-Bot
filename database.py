import sqlite3
from datetime import datetime

def get_db(chat_id: int):
    db_name = f"db_group_{chat_id}.db"
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Таблиця пар (заручені/одружені)
    c.execute("""
    CREATE TABLE IF NOT EXISTS couples (
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        wed_date TEXT NOT NULL,
        PRIMARY KEY (user1_id, user2_id)
    )
    """)

    # Таблиця користувачів (для активності)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        last_active TEXT
    )
    """)

    conn.commit()
    return conn

def update_last_active(conn, user_id: int):
    c = conn.cursor()
    now_str = datetime.now().isoformat()
    c.execute("INSERT OR REPLACE INTO users (user_id, last_active) VALUES (?, ?)", (user_id, now_str))
    conn.commit()

def get_last_active(conn, user_id: int):
    c = conn.cursor()
    c.execute("SELECT last_active FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0])
    return None

def add_couple(conn, user1_id: int, user2_id: int):
    c = conn.cursor()
    user1, user2 = sorted([user1_id, user2_id])
    now_str = datetime.now().isoformat()
    try:
        c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1, user2, now_str))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_couple(conn, user_id: int):
    c = conn.cursor()
    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    return c.fetchone()

def remove_couple(conn, user_id: int):
    c = conn.cursor()
    couple = get_couple(conn, user_id)
    if couple:
        user1, user2, _ = couple
        c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (user1, user2))
        conn.commit()
        return True
    return False
