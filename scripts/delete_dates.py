import psycopg2

NEON_URL = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

conn = psycopg2.connect(NEON_URL)
cur  = conn.cursor()

cur.execute("SELECT COUNT(*) FROM exam_ca_articles WHERE published_at::date IN ('2026-05-04', '2026-05-05')")
count = cur.fetchone()[0]
print(f"Articles to delete: {count}")

cur.execute("DELETE FROM exam_ca_articles WHERE published_at::date IN ('2026-05-04', '2026-05-05')")
conn.commit()
print(f"Deleted {cur.rowcount} articles")
conn.close()
