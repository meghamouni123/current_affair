import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    raise EnvironmentError(
        "\n\n  DATABASE_URL is not set!\n"
        "  Add it to your .env file:\n"
        "    DATABASE_URL=postgresql://user:password@localhost:5432/ca_portal\n"
        "  Then run:  python run.py\n"
    )


def get_connection():
    import psycopg2
    import psycopg2.extras
    return psycopg2.connect(DATABASE_URL)


def _placeholders(n: int) -> str:
    return ",".join(["%s"] * n)


def init_db():
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS exam_ca_articles (
                id          SERIAL PRIMARY KEY,
                date        TEXT NOT NULL,
                category    TEXT NOT NULL,
                headline    TEXT NOT NULL,
                summary     TEXT NOT NULL,
                source      TEXT,
                url         TEXT,
                url_hash    TEXT UNIQUE,
                confidence  REAL DEFAULT 0.0,
                word_count  INTEGER DEFAULT 0,
                fetched_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning(f"exam_ca_articles create skipped: {e}")
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id   SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning(f"categories create skipped: {e}")
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_date_category ON exam_ca_articles(date, category)",
        "CREATE INDEX IF NOT EXISTS idx_date          ON exam_ca_articles(date)",
        "CREATE INDEX IF NOT EXISTS idx_category      ON exam_ca_articles(category)",
        "CREATE INDEX IF NOT EXISTS idx_confidence    ON exam_ca_articles(confidence)",
        "CREATE INDEX IF NOT EXISTS idx_url_hash      ON exam_ca_articles(url_hash)",
    ]:
        try:
            cur.execute(idx_sql)
            conn.commit()
        except Exception:
            conn.rollback()
    categories = [
        'Economy & Banking', 'Polity & Governance', 'International Relations',
        'Science & Technology', 'Schemes & Appointments', 'Reports & Indices',
        'Sports', 'Awards & Honours', 'Important Days & Obituaries',
        'Summits & Conferences', 'National News', 'State News',
    ]
    for cat in categories:
        try:
            cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (cat,))
        except Exception:
            pass
    conn.commit()
    conn.close()
    logger.info("PostgreSQL database initialized.")


def insert_article(data: Dict[str, Any]) -> bool:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO exam_ca_articles
                (date, category, headline, summary, source, url,
                 url_hash, confidence, word_count, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url_hash) DO UPDATE SET
                summary    = EXCLUDED.summary,
                confidence = EXCLUDED.confidence,
                url        = EXCLUDED.url,
                fetched_at = EXCLUDED.fetched_at
        """, (
            data.get('date',       str(date.today())),
            data['category'],
            data['headline'],
            data['summary'],
            data.get('source',     ''),
            data.get('url',        ''),
            data.get('url_hash',   ''),
            data.get('confidence', 0.0),
            data.get('word_count', 0),
            data.get('fetched_at', datetime.now().isoformat()),
        ))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error(f"insert_article error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_articles(
    date_filter:     Optional[str] = None,
    category_filter: Optional[str] = None,
    min_confidence:  float         = 0.8,
    limit:           int           = 100,
    offset:          int           = 0,
    date_from:       Optional[str] = None,
    search:          Optional[str] = None,
) -> List[Dict]:
    conn   = get_connection()
    cur    = conn.cursor()
    q      = "SELECT id, date, category, headline, summary, source, confidence, url, word_count, fetched_at FROM exam_ca_articles WHERE confidence >= %s"
    params = [min_confidence]
    if date_filter:
        q += " AND date = %s";      params.append(date_filter)
    elif date_from:
        q += " AND date >= %s";     params.append(date_from)
    if category_filter and category_filter != 'All':
        q += " AND category = %s";  params.append(category_filter)
    if search and search.strip():
        q += " AND (headline ILIKE %s OR summary ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    q += " ORDER BY date DESC, confidence DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    cur.execute(q, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def get_article_count(
    date_filter:     Optional[str] = None,
    category_filter: Optional[str] = None,
    min_confidence:  float         = 0.8,
    date_from:       Optional[str] = None,
    search:          Optional[str] = None,
) -> int:
    conn   = get_connection()
    cur    = conn.cursor()
    q      = "SELECT COUNT(*) FROM exam_ca_articles WHERE confidence >= %s"
    params = [min_confidence]
    if date_filter:
        q += " AND date = %s";      params.append(date_filter)
    elif date_from:
        q += " AND date >= %s";     params.append(date_from)
    if category_filter and category_filter != 'All':
        q += " AND category = %s";  params.append(category_filter)
    if search and search.strip():
        q += " AND (headline ILIKE %s OR summary ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    cur.execute(q, params)
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_categories() -> List[str]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT name FROM categories ORDER BY name")
    cats = [r[0] for r in cur.fetchall()]
    conn.close()
    return cats


def get_dates_with_articles(days: int = 30) -> List[str]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT date FROM exam_ca_articles WHERE confidence >= 0.8 ORDER BY date DESC LIMIT %s", (days,))
    dates = [r[0] for r in cur.fetchall()]
    conn.close()
    return dates


def get_stats() -> Dict:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM exam_ca_articles WHERE confidence >= 0.8")
    total = cur.fetchone()[0]
    cur.execute("SELECT category, COUNT(*) AS cnt FROM exam_ca_articles WHERE confidence >= 0.8 GROUP BY category ORDER BY cnt DESC")
    by_cat = {r[0]: r[1] for r in cur.fetchall()}
    cur.execute("SELECT date, COUNT(*) AS cnt FROM exam_ca_articles WHERE confidence >= 0.8 GROUP BY date ORDER BY date DESC LIMIT 30")
    by_date = {r[0]: r[1] for r in cur.fetchall()}
    today_str  = str(date.today())
    week_dates = [str(date.today() - timedelta(days=i)) for i in range(7)]
    cur.execute(f"SELECT COUNT(*) FROM exam_ca_articles WHERE date IN ({_placeholders(len(week_dates))}) AND confidence >= 0.8", week_dates)
    week_count  = cur.fetchone()[0]
    today_count = by_date.get(today_str, 0)
    conn.close()
    return {"total": total, "by_category": by_cat, "by_date": by_date, "today": today_count, "this_week": week_count}


def url_exists(url_hash: str) -> bool:
    conn   = get_connection()
    cur    = conn.cursor()
    cur.execute("SELECT 1 FROM exam_ca_articles WHERE url_hash = %s", (url_hash,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists
