import sqlite3
from datetime import datetime

def get_db(chat_id: int):
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
        lang TEXT DEFAULT 'uk',
        status TEXT DEFAULT 'Вільний(а)'
    )
    """)

    conn.commit()
    return conn

def get_lang_status(cursor, user_id: int):
    cursor.execute("SELECT lang, status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        lang = row[0] if row[0] else "uk"
        status = row[1] if row[1] else "Вільний(а)"
        return lang, status
    return "uk", "Вільний(а)"

def get_couple(conn, user_id: int):
    c = conn.cursor()
    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    return c.fetchone()

def add_couple(conn, user1_id: int, user2_id: int):
    c = conn.cursor()
    user1, user2 = min(user1_id, user2_id), max(user1_id, user2_id)
    now_str = datetime.now().isoformat()
    try:
        c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1, user2, now_str))
        c.execute("INSERT OR REPLACE INTO users (user_id, lang, status) VALUES (?, COALESCE((SELECT lang FROM users WHERE user_id=?), 'uk'), ?)", (user1, user1, "Одружений(а)"))
        c.execute("INSERT OR REPLACE INTO users (user_id, lang, status) VALUES (?, COALESCE((SELECT lang FROM users WHERE user_id=?), 'uk'), ?)", (user2, user2, "Одружений(а)"))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def update_status_free(conn, user_ids):
    c = conn.cursor()
    c.execute("UPDATE users SET status = 'Вільний(а)' WHERE user_id IN ({seq})".format(
        seq=','.join(['?']*len(user_ids))), user_ids)
    conn.commit()

def update_status_married(conn, user1_id, user2_id):
    c = conn.cursor()
    c.execute("UPDATE users SET status = 'Одружений(а)' WHERE user_id IN (?, ?)", (user1_id, user2_id))
    conn.commit()

def delete_couple(conn, user1_id, user2_id):
    c = conn.cursor()
    user1, user2 = min(user1_id, user2_id), max(user1_id, user2_id)
    c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (user1, user2))
    conn.commit()
