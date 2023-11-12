# feed_checker.py
import feedparser
import requests
import sqlite3
import os

# 環境変数から設定を読み込むか、デフォルトのパスを使用します。
CONFIG_PATH = os.getenv('CONFIG_PATH', '../config.ini')

def load_config(path):
    import configparser
    config = configparser.RawConfigParser()
    config.read(path)
    return config['DEFAULT']['DiscordWebhookUrl'], config['DEFAULT']['RssFeedUrl']

# 設定を読み込みます。
WEBHOOK_URL, RSS_FEED_URL = load_config(CONFIG_PATH)
# Get the directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))
# Construct the path to the database file
DATABASE_PATH = os.path.join(script_dir, '../db/posted_entries.db')
def post_to_discord(entry):
    # Discordに投稿するためのデータを作成します。
    data = {
        "content": f"{entry.title}\n{entry.link}"
    }
    # DiscordのWebhook URLにPOSTリクエストを送信します。
    response = requests.post(WEBHOOK_URL, json=data)
    return response.status_code == 204  # 204は成功のステータスコードです。

def entry_already_posted(entry_id):
    # データベースを確認してエントリが既に投稿されたかどうかをチェックします。
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM posted_entries WHERE id = ?", (entry_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def mark_entry_as_posted(entry_id, entry):
    # エントリをデータベースに記録します。
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO posted_entries (id, title, summary, url) VALUES (?, ?, ?, ?)",
              (entry_id, entry.title, None, entry.link))
    conn.commit()
    conn.close()

def check_feed_and_post_entries():
    # RSSフィードを解析します。
    feed = feedparser.parse(RSS_FEED_URL)
    print(f"Feed Title: {feed.feed.get('title', 'No feed title')}")
    print(f"Feed Entries: {len(feed.entries)}")

    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)  # idがなければ、linkをエントリIDとして使用します。
        if not entry_already_posted(entry_id):  # エントリがまだ投稿されていない場合
            if post_to_discord(entry):  # Discordに投稿を試みます。
                mark_entry_as_posted(entry_id, entry)  # 成功したら、データベースに記録します。
                print(f"Posted to Discord: {entry.title}")
            else:
                print(f"Failed to post to Discord: {entry.title}")

if __name__ == '__main__':
    check_feed_and_post_entries()
