# feed_checker.py
import sqlite3
import feedparser
import requests

# データベースファイルのパス
DATABASE_PATH = 'posted_entries.db'
# DiscordのWebhook URL
WEBHOOK_URL = 'your_webhook_url_here'
# RSSフィードURL
RSS_FEED_URL = 'your_rss_feed_url_here'

def post_to_discord(entry):
    data = {
        "content": entry.title + "\n" + entry.link
    }
    result = requests.post(WEBHOOK_URL, json=data)
    return result.status_code == 204

def entry_already_posted(entry_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM posted_entries WHERE id = ?", (entry_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def mark_entry_as_posted(entry_id, title, summary, url):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO posted_entries (id, title, summary, url) VALUES (?, ?, ?, ?)",
              (entry_id, title, summary, url))
    conn.commit()
    conn.close()

def check_feed_and_post_new_entries(feed_url):
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)  # 'id'属性がない場合は'link'属性を使用
        if not entry_already_posted(entry_id):
            if post_to_discord(entry):
                mark_entry_as_posted(entry_id, entry.title, entry.summary, entry.link)
                print(f"Posted to Discord: {entry.title}")
            else:
                print(f"Failed to post to Discord: {entry.title}")

if __name__ == '__main__':
    check_feed_and_post_new_entries(RSS_FEED_URL)
