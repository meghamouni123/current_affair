import os
import json
import hashlib
import logging
import time
import re
from datetime import datetime, date
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    logger.warning("feedparser not installed. Run: pip install feedparser")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed. Run: pip install requests")

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    logger.warning("trafilatura not installed. Run: pip install trafilatura")

FEEDS_PATH       = os.path.join(os.path.dirname(__file__), '..', 'data', 'rss_feeds.json')
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY", "")

EXAM_KEYWORDS = [
    'government', 'ministry', 'minister', 'parliament', 'lok sabha', 'rajya sabha',
    'cabinet', 'scheme', 'policy', 'bill', 'act', 'law', 'constitution',
    'supreme court', 'high court', 'election', 'commission', 'president', 'governor',
    'rbi', 'reserve bank', 'gdp', 'inflation', 'budget', 'tax', 'gst', 'sebi',
    'bank', 'finance', 'economy', 'trade', 'export', 'import', 'rupee',
    'fiscal', 'monetary', 'repo rate', 'interest rate', 'sensex', 'nifty',
    'isro', 'nasa', 'satellite', 'mission', 'launch', 'technology', 'research',
    'scientist', 'invention', 'discovery', 'space', 'drdo', 'iit', 'innovation',
    'india', 'bilateral', 'agreement', 'mou', 'summit', 'conference', 'united nations',
    'un', 'who', 'wto', 'imf', 'world bank', 'g20', 'brics', 'saarc', 'asean',
    'treaty', 'diplomatic', 'foreign', 'embassy',
    'army', 'navy', 'air force', 'defence', 'military', 'exercise', 'missile',
    'award', 'prize', 'honour', 'appointed', 'elected', 'selected', 'chief',
    'director', 'chairman', 'padma', 'bharat ratna', 'nobel', 'oscar',
    'cricket', 'olympics', 'commonwealth', 'asian games', 'world cup', 'championship',
    'gold medal', 'silver', 'bronze', 'ipl', 'tournament', 'fifa',
    'index', 'report', 'ranking', 'survey', 'data', 'statistics', 'census',
    'climate', 'environment', 'pollution', 'wildlife', 'forest', 'tiger',
    'vaccine', 'health', 'hospital', 'drug', 'medicine', 'aiims', 'icmr',
    'railway', 'highway', 'airport', 'port', 'infrastructure', 'smart city',
    'state', 'district', 'inaugurated', 'launched', 'foundation stone',
]

NOT_RELEVANT_SIGNALS = [
    'entertainment', 'bollywood', 'movie', 'film', 'actor', 'actress',
    'celebrity', 'gossip', 'fashion', 'lifestyle', 'recipe', 'food',
    'horoscope', 'astrology', 'dating', 'relationship', 'hair', 'beauty',
    'cricket match score', 'ipl score',
]


def load_feeds() -> List[Dict]:
    try:
        with open(FEEDS_PATH, 'r') as f:
            data = json.load(f)
        return data.get('feeds', [])
    except Exception as e:
        logger.error(f"Could not load feeds: {e}")
        return []


def make_url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def is_exam_relevant_headline(headline: str) -> bool:
    h = headline.lower()
    for signal in NOT_RELEVANT_SIGNALS:
        if signal in h:
            return False
    for kw in EXAM_KEYWORDS:
        if kw in h:
            return True
    return False


def extract_article_text(url: str, timeout: int = 10) -> Optional[str]:
    if not HAS_REQUESTS:
        return None
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CABot/1.0; +https://ca.example.com)'}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        html = response.text

        if HAS_TRAFILATURA:
            text = trafilatura.extract(html, include_comments=False, include_tables=False)
            if text and len(text.split()) >= 30:
                return text.strip()

        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text.split()) >= 30:
            return text[:3000]
        return None
    except Exception as e:
        logger.debug(f"Failed to extract text from {url}: {e}")
        return None


def parse_feed_date(entry) -> str:
    for attr in ['published_parsed', 'updated_parsed']:
        t = getattr(entry, attr, None)
        if t:
            try:
                return date(*t[:3]).isoformat()
            except Exception:
                pass
    return date.today().isoformat()


def fetch_rss_feed(feed_info: Dict, extract_text: bool = True) -> List[Dict]:
    if not HAS_FEEDPARSER:
        return []

    articles  = []
    feed_url  = feed_info['url']
    feed_name = feed_info['name']

    try:
        parsed = None

        # Try requests first (with timeout), fallback to feedparser direct
        if HAS_REQUESTS:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
                resp = requests.get(feed_url, headers=headers, timeout=15)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.content)
            except Exception:
                pass

        # Fallback: feedparser direct (uses its own urllib with different headers)
        if parsed is None or (parsed.bozo and not parsed.entries):
            parsed = feedparser.parse(feed_url)

        if not parsed or (parsed.bozo and not parsed.entries):
            return []

        for entry in parsed.entries[:20]:
            try:
                title    = getattr(entry, 'title',   '').strip()
                link     = getattr(entry, 'link',    '').strip()
                summary  = getattr(entry, 'summary', '').strip()
                pub_date = parse_feed_date(entry)

                if not title or not link:
                    continue

                url_hash    = make_url_hash(link)
                description = re.sub(r'<[^>]+>', ' ', summary)
                description = re.sub(r'\s+', ' ', description).strip()

                full_text = None
                if extract_text and len(description.split()) < 50:
                    full_text = extract_article_text(link)

                text_for_classification = full_text or description or title
                if len(text_for_classification.split()) < 15:
                    text_for_classification = title

                articles.append({
                    'headline':      title,
                    'text':          text_for_classification,
                    'url':           link,
                    'url_hash':      url_hash,
                    'source':        feed_name,
                    'date':          pub_date,
                    'fetched_at':    datetime.now().isoformat(),
                    'feed_category': feed_info.get('category', ''),
                })
                time.sleep(0.05)

            except Exception as e:
                logger.debug(f"Entry error in {feed_name}: {e}")
                continue

    except Exception as e:
        logger.warning(f"Feed fetch error for {feed_name} ({feed_url}): {e}")

    return articles


def fetch_all_rss_feeds(max_feeds: int = None, extract_text: bool = True) -> List[Dict]:
    feeds = load_feeds()
    if max_feeds:
        feeds = feeds[:max_feeds]

    all_articles = []
    seen_hashes  = set()

    for i, feed in enumerate(feeds):
        logger.info(f"[{i+1}/{len(feeds)}] Fetching: {feed['name']}")
        articles = fetch_rss_feed(feed, extract_text=extract_text)
        for article in articles:
            h = article['url_hash']
            if h not in seen_hashes:
                seen_hashes.add(h)
                all_articles.append(article)
        time.sleep(0.5)

    logger.info(f"Total unique articles fetched: {len(all_articles)}")
    return all_articles


def fetch_newsdata_api(api_key: str, country: str = "in", language: str = "en", size: int = 50) -> List[Dict]:
    if not HAS_REQUESTS or not api_key:
        return []

    articles = []
    try:
        response = requests.get(
            "https://newsdata.io/api/1/news",
            params={'apikey': api_key, 'country': country, 'language': language, 'size': size},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        for item in data.get('results', []):
            title    = item.get('title', '').strip()
            content  = item.get('content') or item.get('description') or ''
            link     = item.get('link', '')
            pub_date = item.get('pubDate', '')[:10] if item.get('pubDate') else str(date.today())

            if not title or not link:
                continue

            text = re.sub(r'<[^>]+>', ' ', content).strip() or title
            articles.append({
                'headline':   title,
                'text':       text,
                'url':        link,
                'url_hash':   make_url_hash(link),
                'source':     'NewsData.io',
                'date':       pub_date,
                'fetched_at': datetime.now().isoformat(),
            })
    except Exception as e:
        logger.error(f"NewsData.io API error: {e}")

    return articles


def fetch_recent_news(
    use_rss: bool = True,
    use_api: bool = True,
    max_rss_feeds: int = None,
    extract_full_text: bool = False
) -> List[Dict]:
    articles = []

    if use_rss:
        rss_articles = fetch_all_rss_feeds(max_feeds=max_rss_feeds, extract_text=extract_full_text)
        articles.extend(rss_articles)
        logger.info(f"RSS: {len(rss_articles)} articles")

    if use_api and NEWSDATA_API_KEY:
        api_articles = fetch_newsdata_api(NEWSDATA_API_KEY)
        articles.extend(api_articles)
        logger.info(f"NewsData API: {len(api_articles)} articles")

    seen   = set()
    unique = []
    for a in articles:
        if a['url_hash'] not in seen:
            seen.add(a['url_hash'])
            unique.append(a)

    logger.info(f"Total unique after dedup: {len(unique)}")
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = fetch_all_rss_feeds(max_feeds=3, extract_text=False)
    for a in articles[:5]:
        print(f"  [{a['date']}] {a['headline'][:80]}")
    print(f"Total: {len(articles)}")
