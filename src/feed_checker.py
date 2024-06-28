import feedparser
import requests
import sqlite3
import os
import logging
import configparser
from bs4 import BeautifulSoup
import openai
from newspaper import Article
import datetime

# スクリプトのディレクトリとデータベースのパスを取得
script_dir = os.path.dirname(os.path.realpath(__file__))
DATABASE_PATH = os.path.join(script_dir, '../db/posted_entries.db')

# ロガーの設定
logging.basicConfig(level=logging.INFO, filename=os.path.join(script_dir, '../logs/rss2discord.log'), filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(path):
    config = configparser.RawConfigParser()
    try:
        config.read(path)
        # OpenAIの設定を読み込む
        openai_config = {
            'api_key': config['OpenAI']['APIKey']
        }

        # Notionの設定を読み込む
        notion_config = {
            'token': config['Notion']['Token'],
            'database_id': config['Notion']['DatabaseId']
        }

        # 各ユーザーの設定を読み込む
        users_config = {}
        for section in config.sections():
            if section not in ['OpenAI', 'Notion']:
                webhook_url = config.get(section, 'DiscordWebhookUrl', fallback=None)
                feed_urls = config.get(section, 'RssFeedUrls', fallback=None)
                if webhook_url and feed_urls:
                    users_config[section] = {
                        'webhook_url': webhook_url,
                        'feed_urls': [url.strip() for url in feed_urls.split(',')]
                    }
        return openai_config, notion_config, users_config
    except KeyError as e:
        logging.error(f"Missing key in config file: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading config: {e}")
    return None, None, None  # エラーが発生した場合



def fetch_article_content(url):
    """
    与えられたURLからウェブページの内容を取得し、HTMLタグを除去して本文を返す
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # ここで適切なHTML要素を選択して本文を抽出する
            # 例: soup.find('div', class_='article-body').get_text()
            return soup.get_text()
        else:
            return ""
    except requests.exceptions.RequestException:
        return ""

def extract_content(entry):
    content = "No Content"
    article = Article(entry.link)
    article.download()
    article.parse()
    # if not article.text:
    #     content = article.text
    # return content
    return article.text

def post_to_discord(entry, summry, webhook_url):
    """ 
    Discordにエントリのタイトル、リンク、本文を投稿する
    """
    
    title = f"## {entry.title}"
    link = entry.link
    content = extract_content(entry)  # 本文を抽出
    discord_message = f"{title}\n{link}\n{summry}"  # タイトル、リンク、本文を組み合わせる
    try:
        data = {"content": discord_message}
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            logging.info(f"Successfully posted to Discord: {entry.title}")
        else:
            logging.warning(f"Failed to post to Discord: {entry.title} - Status Code: {response.status_code}, Response: {response.text}")
        return response.status_code == 204
    except requests.exceptions.RequestException as e:
        logging.error(f"Error posting to Discord: {e}")
        return False

def post_to_notion(database_id, token, title, content,summury, article_url, user_name,posted_date):
    try:
        notion_api_url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2021-05-13"
        }
    
        data = {
            "parent": {"database_id": database_id},
            "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Content": {"rich_text": [{"text": {"content": content}}]},
            "Summry": {"rich_text": [{"text": {"content": summury}}]},
            "URL": {"url": article_url},
            "Category": {"select": {"name": user_name}},
            "PostedDate": {"date": {"start": posted_date}}
            }
        }
        response = requests.post(notion_api_url, headers=headers, json=data)
        if response.status_code == 200:
            logging.info(f"Successfully posted to Notion: {title}")
        else:
            logging.warning(f"Failed to post to Notion: {title} - Response: {response.status_code} - {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error(f"Error posting to Notion: {e}")
        return False
    
# splite3を使ってデータベースに登録済みのエントリかどうかを確認する
def entry_already_posted(entry_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM posted_entries WHERE id = ?", (entry_id,))
        exists = c.fetchone() is not None
        return exists
    except sqlite3.Error as e:
        logging.error(f"Database error while checking if entry is posted: {e}")
        return False
    finally:
        conn.close()
# splite3を使ってデータベースにエントリを登録する
def mark_entry_as_posted(entry_id, entry):
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
        
# notionのDBに登録済のエントリかどうかを確認する
def entry_already_posted_from_notion(notion_config,entry_id):
    try:
        notion_api_url = "https://api.notion.com/v1/databases/{database_id}/query".format(database_id=notion_config['database_id'])
        headers = {
            "Authorization": "Bearer {token}".format(token=notion_config['token']),
            "Content-Type": "application/json",
            "Notion-Version": "2021-05-13"
        }
        data = {
            "filter": {
                "property": "URL",
                "url": {
                    "equals": entry_id
                }
            }
        }
        response = requests.post(notion_api_url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            # レスポンスにエントリが含まれているかどうかを確認(true/false)
            return len(result.get('results', [])) > 0
        else:
            logging.warning("Failed to query Notion database: {status_code} - {response_text}".format(
                status_code=response.status_code, response_text=response.text
            ))
    except requests.exceptions.RequestException as e:
        logging.error("Error querying Notion database: {error}".format(error=e))
    return False

def summarize_with_openai_api(text, api_key):
    openai.api_key = api_key
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "150文字の日本語要約をしてください。"},
                {"role": "user", "content": text}
            ],
            temperature=0.7,  # 温度を調整
            max_tokens=1024,  # トークン数を調整
            top_p=1,
            frequency_penalty=0,
            # logprobs=0,
            presence_penalty=0
        )
        if response.choices:
            # print(response.choices)
            summary = response.choices[0].message.content 
            return summary
        else:
            logging.error("OpenAI API response is empty.")
            return None
    # except openai.error.OpenAIError as e:
    #     logging.error(f"OpenAI API error: {e} - Response: {getattr(e, 'response', 'No response')}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    return None

def get_entry_date(entry):
    if hasattr(entry, 'published'):
        return entry.published
    elif hasattr(entry, 'updated'):
        return entry.updated
    elif 'dc:date' in entry:
        return entry['dc:date']
    elif hasattr(entry, 'pubDate'):
        return entry.pubDate
    else:
        return datetime.datetime.now().isoformat()

    
    
def check_feed_and_post_entries(openai_config, notion_config, users_config):
    for user, config in users_config.items():
        webhook_url = config['webhook_url']
        for feed_url in config['feed_urls']:
            feed = feedparser.parse(feed_url)
            logging.info(f"{user} - Feed Title: {feed.feed.get('title', 'No feed title')}")
            logging.info(f"{user} - Feed Entries: {len(feed.entries)}")

            # for entry in feed.entries:
            #     entry_id = entry.link
            #     if not entry_already_posted(entry_id):
            #         content = extract_content(entry)
            #         summury = summarize_with_openai_api(content,openai_config['api_key'])
            #         if post_to_discord(entry,summury, webhook_url):
            #             mark_entry_as_posted(entry_id, entry)
            #             logging.info(f"Posted to Discord: {entry.title}")
            #             published = get_entry_date(entry)
            #             post_to_notion(notion_config['database_id'], notion_config['token'], entry.title, extract_content(entry), summury, entry.link, user, published)

            for entry in feed.entries:
                entry_id = entry.link
                if not entry_already_posted(entry_id):
                    content = extract_content(entry)
                    summury = summarize_with_openai_api(content,openai_config['api_key'])
                    if post_to_discord(entry,summury, webhook_url):
                        mark_entry_as_posted(entry_id, entry)
                        logging.info(f"Posted to Discord: {entry.title}")
                        published = get_entry_date(entry)
                        post_to_notion(notion_config['database_id'], notion_config['token'], entry.title, extract_content(entry), summury, entry.link, user, published)


if __name__ == '__main__':
    CONFIG_PATH = os.getenv('CONFIG_PATH', '../config.ini')
    openai_config, notion_config, users_config = load_config(CONFIG_PATH)
    check_feed_and_post_entries(openai_config, notion_config, users_config)