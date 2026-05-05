"""
delete_today.py — Delete all articles inserted/published today (2026-05-05)
Run: python scripts/delete_today.py
"""
import psycopg2
from datetime import date

DATABASE_URL = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

TODAY = str(date.today())  # 2026-05-05

conn = psycopg2.connect(DATABASE_URL)
cur  = conn.cursor()

# Count first
cur.execute(
    "SELECT COUNT(*) FROM exam_ca_articles WHERE published_at::date = %s::date",
    (TODAY,)
)
count = cur.fetchone()[0]
print(f"Articles with published_at = {TODAY}: {count}")

cur.execute(
    "SELECT COUNT(*) FROM exam_ca_articles WHERE fetched_at::date = %s::date",
    (TODAY,)
)
fetched_count = cur.fetchone()[0]
print(f"Articles with fetched_at   = {TODAY}: {fetched_count}")

# Delete anything published OR fetched today
cur.execute(
    """DELETE FROM exam_ca_articles
       WHERE published_at::date = %s::date
          OR fetched_at::date   = %s::date""",
    (TODAY, TODAY)
)
conn.commit()
print(f"\nDeleted {cur.rowcount} articles for {TODAY}")

# Confirm
cur.execute(
    "SELECT COUNT(*) FROM exam_ca_articles WHERE published_at::date = %s::date OR fetched_at::date = %s::date",
    (TODAY, TODAY)
)
remaining = cur.fetchone()[0]
print(f"Remaining today articles: {remaining}")

conn.close()
print("Done.")
