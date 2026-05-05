import psycopg2

NEON_URL = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

conn = psycopg2.connect(NEON_URL)
cur  = conn.cursor()

# Check what's there
cur.execute("SELECT COUNT(*) FROM exam_ca_articles WHERE published_at::date IN ('2026-05-04', '2026-05-05')")
print(f"May 4 & 5 articles in DB: {cur.fetchone()[0]}")

# Delete url_hashes for May 4 & 5 so pipeline can re-fetch them
cur.execute("DELETE FROM exam_ca_articles WHERE published_at::date IN ('2026-05-04', '2026-05-05')")
conn.commit()
print(f"Deleted {cur.rowcount} rows — pipeline will re-fetch on next run")

conn.close()
