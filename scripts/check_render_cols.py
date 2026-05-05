import psycopg2
import sys

RENDER_URL = "postgresql://ca_portal_db_68b1_user:ZRjyNxKDO6PW8gwP8pqvri5SqgZUxFMD@dpg-d790j0nfte5s739cvlug-a.virginia-postgres.render.com/ca_portal_db_68b1"

try:
    print("Connecting to Render...", flush=True)
    conn = psycopg2.connect(RENDER_URL)
    cur = conn.cursor()

    # Total rows
    cur.execute("SELECT COUNT(*) FROM exam_ca_articles")
    print("Render DB alive. Total rows:", cur.fetchone()[0], flush=True)

    # Show all columns
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'exam_ca_articles'
        ORDER BY ordinal_position
    """)
    print("\nColumns:", flush=True)
    for row in cur.fetchall():
        print(f"  {row[0]:25s} {row[1]}", flush=True)

    # Sample dates
    cur.execute("""
        SELECT date, COUNT(*) FROM exam_ca_articles 
        GROUP BY date ORDER BY date DESC LIMIT 10
    """)
    print("\nDate distribution (top 10):", flush=True)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} articles", flush=True)

    conn.close()
except Exception as e:
    print("Render DB error:", e, flush=True)
    sys.exit(1)
