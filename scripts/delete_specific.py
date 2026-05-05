import psycopg2

NEON_URL = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

conn = psycopg2.connect(NEON_URL)
cur  = conn.cursor()

# Find it first
cur.execute("SELECT id, title, published_at::date FROM exam_ca_articles WHERE title ILIKE '%MHT CET%'")
rows = cur.fetchall()
print(f"Found {len(rows)} matching articles:", flush=True)
for r in rows:
    print(f"  id={r[0]} | {r[2]} | {r[1]}", flush=True)

# Delete all exam schedule / admit card / hall ticket type articles that slipped through
cur.execute("""
    DELETE FROM exam_ca_articles
    WHERE title ILIKE '%admit card%'
       OR title ILIKE '%hall ticket%'
       OR title ILIKE '%exam schedule%'
       OR title ILIKE '%city intimation%'
       OR title ILIKE '%answer key%'
       OR title ILIKE '%result declared%'
       OR title ILIKE '%cut off%'
       OR title ILIKE '%merit list%'
       OR title ILIKE '%MHT CET%'
       OR title ILIKE '%NEET%exam%'
       OR title ILIKE '%JEE%exam%'
       OR title ILIKE '%board exam%'
       OR title ILIKE '%CBSE result%'
       OR title ILIKE '%ICSE result%'
       OR title ILIKE '%weather forecast%'
       OR title ILIKE '%rain alert%'
       OR title ILIKE '%rain today%'
       OR title ILIKE '%temperature today%'
""")
conn.commit()
print(f"\nDeleted {cur.rowcount} irrelevant articles", flush=True)

# Confirm total remaining
cur.execute("SELECT COUNT(*) FROM exam_ca_articles")
print(f"Total remaining: {cur.fetchone()[0]}", flush=True)

conn.close()
print("Done.", flush=True)
