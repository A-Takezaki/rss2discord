# feed_checker.py
import feedparser
import requests
import sqlite3
import os

# CONFIGファイルのパスを環境変数から取得、なければデフォルトのパスを使用
CONFIG_PATH = os.getenv('CONFIG_PATH', '../config.ini')

def load_config(path):
    # RawConfigParserを使用してCONFIGファイルを読み込み、設定値を取得
    import configparser
    config = configparser.RawConfigParser()
    config.read(path)
    return config['DEFAULT']['DiscordWebhookUrl'], config['DEFAULT']['RssFeedUrl']

# CONFIGファイルからDiscordのWebhook URLとRSSフィードURLを読み込む
WEBHOOK_URL, RSS_FEED_URL = load_config(CONFIG_PATH)

# スクリプトが存在するディレクトリの絶対パスを取得
script_dir = os.path.dirname(os.path.realpath(__file__))
# データベースファイルへの絶対パスを構築
DATABASE_PATH = os.path.join(script_dir, '../db/posted_entries.db')

def post_to_discord(entry):
    # Discordへの投稿内容を準備
    data = {
        "content": f"{entry.title}\n{entry.link}"
    }
    # DiscordのWebhook URLへ投稿
    response = requests.post(WEBHOOK_URL, json=data)
    # ステータスコード204が返れば成功
    return response.status_code == 204

def entry_already_posted(entry_id):
    # 指定されたIDのエントリがデータベースに存在するか確認
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM posted_entries WHERE id = ?", (entry_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def mark_entry_as_posted(entry_id, entry):
    # エントリをデータベースに記録（summaryは現在使用しないためNoneを挿入）
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO posted_entries (id, title, url) VALUES (?, ?, ?)",
              (entry_id, entry.title, entry.link))
    conn.commit()
    conn.close()

def check_feed_and_post_entries():
    # RSSフィードを解析してエントリを処理
    feed = feedparser.parse(RSS_FEED_URL)
    # フィードのタイトルとエントリ数を出力
    print(f"Feed Title: {feed.feed.get('title', 'No feed title')}")
    print(f"Feed Entries: {len(feed.entries)}")

    # 取得したエントリごとに処理
    for entry in feed.entries:
        entry_id = entry.link # linkをidとして使用
        # 未投稿のエントリのみを処理
        if not entry_already_posted(entry_id):
            # Discordへの投稿を試みる
            if post_to_discord(entry):
                # 投稿成功したらデータベースに記録
                mark_entry_as_posted(entry_id, entry)
                print(f"Posted to Discord: {entry.title}")
            else:
                # 投稿失敗を出力
                print(f"Failed to post to Discord: {entry.title}")

# スクリプトのメイン処理を実行
if __name__ == '__main__':
    check_feed_and_post_entries()
