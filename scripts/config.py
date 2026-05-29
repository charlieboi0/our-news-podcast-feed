import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
PATH_TO_EPISODES = SCRIPT_DIR.parent / 'episodes'
STATE_FILE = SCRIPT_DIR / 'state.json'

# Target release window for the new episode
TARGET_HOUR = 21  # 9 PM
TARGET_MINUTE = 15

SOURCE_FEED_URL = "https://example.com/source-local-news-feed.xml"

def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable {name} is required.")
    return value

MODULATE_API_KEY = require_env("MODULATE_API_KEY")
DEEPSEEK_API_KEY = require_env("DEEPSEEK_API_KEY")
IA_ACCESS_KEY = require_env("IA_ACCESS_KEY_ID")
IA_SECRET_KEY = require_env("IA_SECRET_ACCESS_KEY")

IA_ITEM_NAME = 'our-news-podcast-unofficial'

NAMESPACES = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wfw': 'http://wellformedweb.org/CommentAPI/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'atom': 'http://www.w3.org/2005/Atom',
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'googleplay': 'http://www.google.com/schemas/play-podcasts/1.0',
    'spotify': 'http://www.spotify.com/ns/rss',
    'podcast': 'https://podcastindex.org/namespace/1.0',
    'media': 'http://search.yahoo.com/mrss/',
}