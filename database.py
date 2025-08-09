import sqlite3
from contextlib import closing

DB_NAME = "lovebot.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    with closing(get_connection()) as conn:
        c = conn.cursor()
        # Таблиця користувачів: user_id, username, fullname, статус (вільний або одружений)
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                fullname TEXT,
                status TEXT DEFAULT 'Вільний(а)'
            )
        ''')

        # Таблиця пар: двоє користувачів і дата весілля
        c.execute('''
            CREATE TABLE IF NOT EXISTS couples (
                user1_id INTEGER,
                user2_id INTEGER,
                wed_date TEXT,
                PRIMARY KEY(user1_id, user2_id),
                FOREIGN KEY(user1_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(user2_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

def add_or_update_user(user_id: int, username: str, fullname: str):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO users (user_id, username, fullname)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                fullname=excluded.fullname
        ''', (user_id, username, fullname))
        conn.commit()

def get_user_by_username(username: str):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('SELECT user_id, username, fullname, status FROM users WHERE username = ?', (username,))
        return c.fetchone()

def get_user_by_id(user_id: int):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('SELECT user_id, username, fullname, status FROM users WHERE user_id = ?', (user_id,))
        return c.fetchone()

def is_user_married(user_id: int):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('SELECT 1 FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
        return c.fetchone() is not None

def add_couple(user1_id: int, user2_id: int, wed_date: str):
    user1_id, user2_id = sorted((user1_id, user2_id))
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, wed_date))
        c.execute('UPDATE users SET status = ? WHERE user_id IN (?, ?)', ('Одружений(а)', user1_id, user2_id))
        conn.commit()

def remove_couple(user_id: int):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
        row = c.fetchone()
        if not row:
            return False
        user1_id, user2_id = row
        c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (user1_id, user2_id))
        c.execute('UPDATE users SET status = ? WHERE user_id IN (?, ?)', ('Вільний(а)', user1_id, user2_id))
        conn.commit()
        return True

def get_couple_by_user(user_id: int):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
        return c.fetchone()

def get_all_couples():
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute('SELECT user1_id, user2_id, wed_date FROM couples')
        return c.fetchall()
