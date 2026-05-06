"""
migrate_may23_to_neon.py
Copies May 2 & 3 articles from Render DB → Neon DB.
Skips rows where url_hash already exists in Neon (safe to re-run).
Does NOT clear Neon — only inserts missing rows.
"""

import psycopg2

RENDER_URL = "postgresql://ca_portal_db_68b1_user:ZRjyNxKDO6PW8gwP8pqvri5SqgZUxFMD@dpg-d790j0nfte5s739cvlug-a.virginia-postgres.render.com/ca_portal_db_68b1"
NEON_URL   = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

TARGET_DATES = ('2026-05-02', '2026-05-03')
BATCH_SIZE   = 50


def migrate():
    print("Connecting to Render DB...")
    src     = psycopg2.connect(RENDER_URL)
    src_cur = src.cursor()

    print("Connecting to Neon DB...")
    dst     = psycopg2.connect(NEON_URL)
    dst_cur = dst.cursor()

    # Count in Render for May 2 & 3
    src_cur.execute("""
        SELECT COUNT(*) FROM exam_ca_articles
        WHERE date IN %s
    """, (TARGET_DATES,))
    total = src_cur.fetchone()[0]
    print(f"Render DB — May 2 & 3 articles: {total}")

    if total == 0:
        print("Nothing to migrate.")
        src.close(); dst.close()
        return

    # Fetch May 2 & 3 rows from Render
    src_cur.execute("""
        SELECT headline, summary, category, source, url,
               url_hash, confidence, word_count, date, fetched_at
        FROM exam_ca_articles
        WHERE date IN %s
        ORDER BY date DESC
    """, (TARGET_DATES,))
    rows = src_cur.fetchall()
    print(f"Fetched {len(rows)} rows from Render")

    inserted = 0
    skipped  = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        for row in batch:
            try:
                date_str     = str(row[8] or "2026-05-02")[:10]
                published_at = f"{date_str}T00:00:00+00:00"
                fetched_at   = str(row[9]) if row[9] else published_at

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
                if dst_cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  Row error: {e}")
                dst.rollback()
                skipped += 1
                continue

        dst.commit()
        done = min(i + BATCH_SIZE, len(rows))
        print(f"  Progress: {done}/{len(rows)} | inserted={inserted} skipped={skipped}")

    # Verify in Neon
    dst_cur.execute("""
        SELECT published_at::date AS d, COUNT(*) 
        FROM exam_ca_articles 
        WHERE published_at::date IN ('2026-05-02', '2026-05-03')
        GROUP BY d ORDER BY d
    """)
    print("\nNeon DB — May 2 & 3 after migration:")
    for row in dst_cur.fetchall():
        print(f"  {row[0]}: {row[1]} articles")

    src.close()
    dst.close()
    print(f"\nDone! Inserted: {inserted} | Skipped (already existed): {skipped}")


if __name__ == "__main__":
    migrate()
