"""
json_exporter.py — Export articles from PostgreSQL to static JSON files
Called by GitHub Actions after pipeline runs
"""

import os
import sys
import json
import logging
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)


def export_articles_json(output_path: str) -> int:
    from database import get_connection

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, title, summary, category, source, url,
               relevance_score, published_at::date AS published_date
        FROM exam_ca_articles
        WHERE relevance_score >= 0.8
        ORDER BY published_at DESC, relevance_score DESC
        LIMIT 500
    """)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    # Convert date objects to strings
    for row in rows:
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                row[k] = v.isoformat()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "articles":   rows,
            "count":      len(rows),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(rows)} articles → {output_path}")
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'data', 'articles.json')
    n = export_articles_json(out)
    print(f"Exported {n} articles")
