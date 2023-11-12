# # feed_checker.py
# import feedparser
# import requests

# # フィードのURLを設定（必要に応じてエンコードを確認）
# # feed_url = "https://b.hatena.ne.jp/q/%E3%82%BB%E3%82%AD%E3%83%A5%E3%83%AA%E3%83%86%E3%82%A3?mode=rss"
# feed_url = "https://www.jpcert.or.jp/rss/jpcert-all.rdf"

# # フィードの内容を解析
# # feed = feedparser.parse(feed_content)
# feed = feedparser.parse(feed_url)

# # フィードのタイトルとエントリ数を表示
# print(f"Feed Title: {feed.feed.get('title', 'No feed title')}")
# print(f"Feed Entries: {len(feed.entries)}")

# # 他のコード...


# # feed_checker.py
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

DATABASE_PATH = '../db/posted_entries.db'  # データベースファイルへのパスを更新してください。

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
              (entry_id, entry.title, entry.summary, entry.link))
    conn.commit()
    conn.close()

def check_feed_and_post_entries():
# CONFIGファイルからURLを読み取った後に確認
    print(f"Loaded RSS feed URL: {RSS_FEED_URL}")
    # RSSフィードを解析します。
    feed = feedparser.parse(RSS_FEED_URL)
    print(feed)
    # print(f"Feed Title: {feed.feed.get('title', 'No feed title')}")
    # print(f"Feed Entries: {len(feed.entries)}")

    # for entry in feed.entries:
    #     entry_id = entry.get('id', entry.link)  # idがなければ、linkをエントリIDとして使用します。
    #     if not entry_already_posted(entry_id):  # エントリがまだ投稿されていない場合
    #         if post_to_discord(entry):  # Discordに投稿を試みます。
    #             mark_entry_as_posted(entry_id, entry)  # 成功したら、データベースに記録します。
    #             print(f"Posted to Discord: {entry.title}")
    #         else:
    #             print(f"Failed to post to Discord: {entry.title}")

if __name__ == '__main__':
    check_feed_and_post_entries()
