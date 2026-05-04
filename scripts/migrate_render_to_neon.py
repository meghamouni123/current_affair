"""
migrate_render_to_neon.py
Copies exam_ca_articles from Render PostgreSQL -> Neon PostgreSQL.
Skips rows where url_hash already exists in Neon (safe to re-run).
"""

import psycopg2

RENDER_URL = "postgresql://ca_portal_db_68b1_user:ZRjyNxKDO6PW8gwP8pqvri5SqgZUxFMD@dpg-d790j0nfte5s739cvlug-a.virginia-postgres.render.com/ca_portal_db_68b1"
NEON_URL   = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

BATCH_SIZE = 50


def ensure_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_ca_articles (
            id               SERIAL PRIMARY KEY,
            title            TEXT NOT NULL,
            summary          TEXT NOT NULL,
            category         TEXT NOT NULL,
            source           TEXT,
            url              TEXT,
            url_hash         TEXT UNIQUE,
            relevance_score  REAL DEFAULT 0.0,
            word_count       INTEGER DEFAULT 0,
            published_at     TIMESTAMPTZ DEFAULT NOW(),
            fetched_at       TIMESTAMPTZ DEFAULT NOW(),
            is_visible       BOOLEAN DEFAULT TRUE
        )
    """)


def migrate():
    print("Connecting to Render DB...")
    src = psycopg2.connect(RENDER_URL)
    src_cur = src.cursor()

    print("Connecting to Neon DB...")
    dst = psycopg2.connect(NEON_URL)
    dst_cur = dst.cursor()

    ensure_table(dst_cur)
    dst.commit()

    # Clear Neon DB first
    print("Clearing Neon DB...")
    dst_cur.execute("DELETE FROM exam_ca_articles")
    dst.commit()
    print("  Neon DB cleared.")

    # Fetch all from Render
    print("Fetching articles from Render...")
    src_cur.execute("""
        SELECT headline, summary, category, source, url,
               url_hash, confidence, word_count, date, fetched_at
        FROM exam_ca_articles
        ORDER BY created_at DESC
    """)
    rows = src_cur.fetchall()
    print(f"  Render has {len(rows)} articles")

    inserted = 0
    skipped  = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        for row in batch:
            try:
                date_str     = (row[8] or "2025-01-01")[:10]
                published_at = f"{date_str}T00:00:00+00:00"
                fetched_at   = row[9] or published_at

                dst_cur.execute("""
                    INSERT INTO exam_ca_articles
                        (title, summary, category, source, url,
                         url_hash, relevance_score, word_count,
                         published_at, fetched_at, is_visible)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (url_hash) DO NOTHING
                """, (
                    row[0], row[1], row[2], row[3], row[4],
                    row[5], row[6], row[7],
                    published_at, fetched_at, True,
                ))
                inserted += 1
            except Exception as e:
                print(f"  Row error: {e}")
                dst.rollback()
                continue

        dst.commit()
        done = min(i + BATCH_SIZE, len(rows))
        print(f"  {done}/{len(rows)} | inserted={inserted}")

    src.close()
    dst.close()
    print(f"\nDone! Inserted: {inserted} articles into Neon DB.")


if __name__ == "__main__":
    migrate()
