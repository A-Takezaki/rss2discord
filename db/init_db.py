# init_db.py
import sqlite3

# データベースファイルのパス
DATABASE_PATH = 'posted_entries.db'

def create_database():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE posted_entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT NOT NULL,
            posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            important BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
