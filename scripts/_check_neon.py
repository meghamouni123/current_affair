import psycopg2
NEON_URL = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"
try:
    print("Connecting to Neon...", flush=True)
    conn = psycopg2.connect(NEON_URL)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM exam_ca_articles")
    print("Neon alive. Total:", cur.fetchone()[0], flush=True)
    cur.execute("SELECT published_at::date, COUNT(*) FROM exam_ca_articles GROUP BY 1 ORDER BY 1 DESC LIMIT 10")
    print("Date distribution:", flush=True)
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}", flush=True)
    conn.close()
except Exception as e:
    print("Neon error:", e, flush=True)
