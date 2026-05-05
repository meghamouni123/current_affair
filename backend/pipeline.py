"""
pipeline.py — ML Pipeline (Fetch → Classify → Summarize → Store)
Runs on: GitHub Actions (daily, free 7GB RAM runner)
NOT loaded by: render_server.py (that's DB-read only)
"""

import os
import sys
import logging
import json
from datetime import datetime, date
from typing import List, Dict, Optional
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, insert_article, url_exists, get_stats
from classifier import get_classifier
from summarizer import generate_summary

import re

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD       = 0.80
DEDUP_SIMILARITY_THRESHOLD = 0.92   # semantic similarity — same meaning different words
HEADLINE_SIMILARITY_THRESHOLD = 0.75  # word-overlap — exact/near-identical headlines


def _normalize_headline(h: str) -> str:
    """Lowercase, remove punctuation, collapse spaces."""
    h = h.lower()
    h = re.sub(r'[^a-z0-9\s]', ' ', h)
    return re.sub(r'\s+', ' ', h).strip()


def _headline_similarity(a: str, b: str) -> float:
    """Jaccard similarity on word sets."""
    wa = set(_normalize_headline(a).split())
    wb = set(_normalize_headline(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


class Pipeline:
    def __init__(self):
        self.classifier = get_classifier()
        self._embedding_cache: List[np.ndarray] = []
        self._url_hash_cache: set = set()
        self._headline_cache: List[str] = []
        self._processed_count = 0
        self._stored_count    = 0
        self._skipped_count   = 0

    def _is_duplicate_by_embedding(self, embedding: np.ndarray) -> bool:
        if not self._embedding_cache:
            return False
        from sklearn.metrics.pairwise import cosine_similarity
        cache_matrix = np.vstack(self._embedding_cache)
        sims = cosine_similarity(embedding.reshape(1, -1), cache_matrix)[0]
        return float(np.max(sims)) > DEDUP_SIMILARITY_THRESHOLD

    def _is_duplicate_by_headline(self, headline: str) -> bool:
        """Catch same story from different sources using word-overlap."""
        for cached in self._headline_cache:
            if _headline_similarity(headline, cached) >= HEADLINE_SIMILARITY_THRESHOLD:
                return True
        return False

    def process_article(self, article: Dict) -> Optional[Dict]:
        url_hash = article.get('url_hash', '')
        headline = article.get('headline', '').strip()
        text     = article.get('text', '').strip()
        url      = article.get('url', '')

        if url_hash:
            if url_hash in self._url_hash_cache:
                return None
            if url_exists(url_hash):
                self._url_hash_cache.add(url_hash)
                return None

        if len(text.split()) < 100:
            text = headline

        full_text = f"{headline}. {text}" if headline not in text else text

        is_relevant, category, confidence = self.classifier.is_exam_relevant(
            full_text,
            threshold=CONFIDENCE_THRESHOLD,
            feed_category=article.get('feed_category', '')
        )
        self._processed_count += 1

        if not is_relevant:
            self._skipped_count += 1
            if url_hash:
                self._url_hash_cache.add(url_hash)
            return None

        embedding = self.classifier.get_embedding(full_text)

        if self._is_duplicate_by_headline(headline):
            self._skipped_count += 1
            logger.debug(f"Headline dedup: {headline[:60]}")
            if url_hash:
                self._url_hash_cache.add(url_hash)
            return None

        if self._is_duplicate_by_embedding(embedding):
            self._skipped_count += 1
            if url_hash:
                self._url_hash_cache.add(url_hash)
            return None

        self._embedding_cache.append(embedding)
        if len(self._embedding_cache) > 700:
            self._embedding_cache = self._embedding_cache[-700:]
        self._headline_cache.append(headline)
        if len(self._headline_cache) > 700:
            self._headline_cache = self._headline_cache[-700:]

        logger.info(f"✓ [{category}] ({confidence:.2f}) {headline[:70]}")

        summary = generate_summary(headline, text, num_bullets=6)

        if summary is None:
            self._skipped_count += 1
            if url_hash:
                self._url_hash_cache.add(url_hash)
            return None

        # Reject summaries with less than 3 bullet points
        bullet_count = summary.count('•')
        if bullet_count < 3:
            self._skipped_count += 1
            if url_hash:
                self._url_hash_cache.add(url_hash)
            return None

        stored = {
            'date':       article.get('date', str(date.today())),
            'category':   category,
            'headline':   headline,
            'summary':    summary,
            'source':     article.get('source', ''),
            'url':        url,
            'url_hash':   url_hash,
            'confidence': round(confidence, 4),
            'word_count': len(text.split()),
            'fetched_at': article.get('fetched_at', datetime.now().isoformat()),
        }

        inserted = insert_article(stored)
        if inserted:
            self._stored_count += 1
            if url_hash:
                self._url_hash_cache.add(url_hash)
            return stored
        return None

    def process_batch(self, articles: List[Dict]) -> List[Dict]:
        stored = []
        for article in articles:
            result = self.process_article(article)
            if result:
                stored.append(result)
        logger.info(
            f"Batch done: {self._processed_count} processed, "
            f"{self._stored_count} stored, {self._skipped_count} skipped"
        )
        return stored

    def get_stats(self) -> Dict:
        return {
            'processed': self._processed_count,
            'stored':    self._stored_count,
            'skipped':   self._skipped_count,
        }


def seed_demo_data():
    init_db()
    pipeline = Pipeline()
    stored = pipeline.process_batch(DEMO_ARTICLES)
    logger.info(f"Seeded {len(stored)} demo articles")
    return len(stored)


def run_pipeline_once(use_rss: bool = True, use_api: bool = True, max_feeds: int = None) -> Dict:
    from news_fetcher import fetch_recent_news

    logger.info("=" * 60)
    logger.info("Starting CA Pipeline (MPNet + BART)")
    logger.info(f"Mode: RSS={use_rss}, API={use_api}, max_feeds={max_feeds or 'all'}")
    logger.info("=" * 60)

    init_db()
    pipeline = Pipeline()

    logger.info("Step 1: Fetching news...")
    articles = fetch_recent_news(use_rss=use_rss, use_api=use_api, max_rss_feeds=max_feeds)
    logger.info(f"Fetched {len(articles)} articles")

    logger.info("Step 2: Classify → Deduplicate → Summarize → Store...")
    stored = pipeline.process_batch(articles)

    stats    = pipeline.get_stats()
    db_stats = get_stats()

    result = {
        'fetched':   len(articles),
        'processed': stats['processed'],
        'stored':    stats['stored'],
        'skipped':   stats['skipped'],
        'db_total':  db_stats['total'],
        'timestamp': datetime.now().isoformat(),
    }
    logger.info(f"Pipeline complete: {result}")
    return result


DEMO_ARTICLES = []


if __name__ == "__main__":
    # GitHub Actions entrypoint
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    import argparse
    parser = argparse.ArgumentParser(description='CA Pipeline — GitHub Actions')
    parser.add_argument('--seed',      action='store_true')
    parser.add_argument('--run',       action='store_true')
    parser.add_argument('--max-feeds', type=int, default=None)
    parser.add_argument('--no-api',    action='store_true')
    args = parser.parse_args()

    if args.seed:
        n = seed_demo_data()
        print(f"Seeded {n} articles")
    else:
        result = run_pipeline_once(
            use_rss=True,
            use_api=not args.no_api and bool(os.environ.get("NEWSDATA_API_KEY")),
            max_feeds=args.max_feeds
        )
        print(json.dumps(result, indent=2))
