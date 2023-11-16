# feed_checker.py
import feedparser
import requests
import sqlite3
import os
import logging
import configparser

# スクリプトのディレクトリとデータベースのパスを取得
script_dir = os.path.dirname(os.path.realpath(__file__))
DATABASE_PATH = os.path.join(script_dir, '../db/posted_entries.db')
# CONFIGファイルのパスを環境変数から取得、なければデフォルトのパスを使用
CONFIG_PATH = os.getenv('CONFIG_PATH', '../config.ini')
# CONFIGファイルから設定を読み込む
# WEBHOOK_URL, RSS_FEED_URL = load_config(CONFIG_PATH)

# ロガーの設定
logging.basicConfig(level=logging.INFO, filename=os.path.join(script_dir, '../logs/rss2discord.log'), filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(path):
    config = configparser.RawConfigParser()
    config.read(path)
    users_config = {}  # ユーザー設定を格納する辞書を初期化

    for section in config.sections():
        # ここで各セクションのWebhook URLを取得します。
        webhook_url = config.get(section, 'DiscordWebhookUrl', fallback=None)
        # セクション内のすべてのRssFeedUrlsエントリを取得します。
        feed_urls = [feed.strip() for feed in config.get(section, 'RssFeedUrls').split(',') if feed.strip()]

        if webhook_url and feed_urls:  # webhook_urlとfeed_urlsが両方とも存在する場合のみ
            users_config[section] = {'webhook_url': webhook_url, 'feed_urls': feed_urls}

    return users_config


def post_to_discord(entry, webhook_url):  # webhook_urlを引数として追加
    data = {"content": f"{entry.title}\n{entry.link}"}
    response = requests.post(webhook_url, json=data)  # webhook_urlを使用してPOSTリクエストを送信
    return response.status_code == 204


def entry_already_posted(entry_id):
    # データベースでエントリが既に投稿されたか確認
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM posted_entries WHERE id = ?", (entry_id,))
        exists = c.fetchone() is not None
        return exists
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        conn.close()

def mark_entry_as_posted(entry_id, entry):
    # データベースにエントリを記録
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO posted_entries (id, title, url) VALUES (?, ?, ?)",
                  (entry_id, entry.title, entry.link))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error inserting into the database: {e}")
    finally:
        conn.close()

def check_feed_and_post_entries(users_config):
    for user, config in users_config.items():
        webhook_url = config['webhook_url']
        for feed_url in config['feed_urls']:
            feed = feedparser.parse(feed_url)
            logging.info(f"{user} - Feed Title: {feed.feed.get('title', 'No feed title')}")
            logging.info(f"{user} - Feed Entries: {len(feed.entries)}")
            
            for entry in feed.entries:
                entry_id = entry.link # linkをidとして使用
                if not entry_already_posted(entry_id):
                    if post_to_discord(entry, webhook_url):  # webhook_urlを引数として渡します
                        mark_entry_as_posted(entry_id, entry)
                        logging.info(f"Posted to Discord: {entry.title}")
                    else:
                        logging.warning(f"Failed to post to Discord: {entry.title}")


if __name__ == '__main__':
    users_config = load_config(CONFIG_PATH)
    check_feed_and_post_entries(users_config)
