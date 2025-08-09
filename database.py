import sqlite3

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
