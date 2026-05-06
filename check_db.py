import os, sys
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

import psycopg2

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    print("❌ DATABASE_URL not found in .env")
    sys.exit(1)

def print_table(headers, rows, max_col=40):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = min(max_col, max(widths[i], len(str(val))))
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    def fmt_row(row):
        return "|" + "|".join(f" {str(v)[:w]:<{w}} " for v, w in zip(row, widths)) + "|"
    print(sep)
    print(fmt_row(headers))
    print(sep)
    for row in rows:
        print(fmt_row(row))
    print(sep)

try:
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'exam_ca_articles'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    print("\n📋 Table: exam_ca_articles — Columns")
    print_table(["Column", "Type"], cols)

    cur.execute("SELECT COUNT(*) FROM exam_ca_articles;")
    total = cur.fetchone()[0]
    print(f"\n📊 Total articles: {total}")

    cur.execute("SELECT category, COUNT(*) as cnt FROM exam_ca_articles GROUP BY category ORDER BY cnt DESC;")
    cats = cur.fetchall()
    print("\n📂 By Category:")
    print_table(["Category", "Count"], cats)

    col_names = [c[0] for c in cols]
    date_col = next((c for c in ['published_at','pub_date','fetched_at'] if c in col_names), col_names[0])
    cur.execute(f"SELECT title, category, {date_col} FROM exam_ca_articles ORDER BY {date_col} DESC LIMIT 5;")
    recent = cur.fetchall()
    print(f"\n🕐 Latest 5 articles (by {date_col}):")
    print_table(["Title", "Category", date_col], recent)

    cur.close()
    conn.close()
    print("\n✅ Done.")

except Exception as e:
    print(f"❌ DB Error: {e}")
