"""
cleanup_irrelevant.py
Remove all irrelevant articles from Neon DB:
- Exam schedules, admit cards, results
- Weather, traffic, general news
- Entertainment, sports scores, viral videos
"""
import psycopg2

NEON_URL = "postgresql://neondb_owner:npg_0GDpJEA6RSBt@ep-lucky-meadow-a4tg4l6c.us-east-1.aws.neon.tech/neondb?sslmode=require"

conn = psycopg2.connect(NEON_URL)
cur  = conn.cursor()

print("Current total:", flush=True)
cur.execute("SELECT COUNT(*) FROM exam_ca_articles")
print(f"  {cur.fetchone()[0]} articles", flush=True)

# Delete all irrelevant patterns
print("\nDeleting irrelevant articles...", flush=True)
cur.execute("""
    DELETE FROM exam_ca_articles
    WHERE 
        -- Exam schedules / admit cards / results
        title ILIKE '%admit card%'
        OR title ILIKE '%hall ticket%'
        OR title ILIKE '%exam schedule%'
        OR title ILIKE '%exam date%'
        OR title ILIKE '%city intimation%'
        OR title ILIKE '%answer key%'
        OR title ILIKE '%result declared%'
        OR title ILIKE '%cut off%'
        OR title ILIKE '%merit list%'
        OR title ILIKE '%CBSE result%'
        OR title ILIKE '%ICSE result%'
        OR title ILIKE '%board exam%'
        OR title ILIKE '%SSC exam%'
        OR title ILIKE '%UPSC exam date%'
        
        -- Weather / traffic
        OR title ILIKE '%weather forecast%'
        OR title ILIKE '%rain alert%'
        OR title ILIKE '%rain today%'
        OR title ILIKE '%temperature today%'
        OR title ILIKE '%traffic jam%'
        OR title ILIKE '%road block%'
        OR title ILIKE '%road accident%'
        
        -- Entertainment / viral / general
        OR title ILIKE '%bollywood%'
        OR title ILIKE '%celebrity%'
        OR title ILIKE '%movie review%'
        OR title ILIKE '%box office%'
        OR title ILIKE '%viral video%'
        OR title ILIKE '%trending video%'
        OR title ILIKE '%funny video%'
        OR title ILIKE '%horoscope%'
        OR title ILIKE '%rashifal%'
        OR title ILIKE '%astrology%'
        OR title ILIKE '%recipe%'
        OR title ILIKE '%cooking tips%'
        
        -- Sports scores (not current affairs)
        OR title ILIKE '%live score%'
        OR title ILIKE '%match score%'
        OR title ILIKE '%IPL score%'
        OR title ILIKE '%fantasy team%'
        
        -- Question format (quiz questions, not news)
        OR (title LIKE '%?%' AND LENGTH(title) < 150)
        
        -- Generic lifestyle
        OR title ILIKE '%weight loss%'
        OR title ILIKE '%beauty tips%'
        OR title ILIKE '%hair care%'
        OR title ILIKE '%skin care%'
        OR title ILIKE '%fashion week%'
        OR title ILIKE '%dating tips%'
""")
conn.commit()
deleted = cur.rowcount
print(f"  Deleted: {deleted} irrelevant articles", flush=True)

# Show remaining by category
print("\nRemaining articles by category:", flush=True)
cur.execute("""
    SELECT category, COUNT(*) 
    FROM exam_ca_articles 
    GROUP BY category 
    ORDER BY COUNT(*) DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]:30s} {row[1]:4d}", flush=True)

# Total
cur.execute("SELECT COUNT(*) FROM exam_ca_articles")
total = cur.fetchone()[0]
print(f"\nTotal remaining: {total} articles", flush=True)

conn.close()
print("Done.", flush=True)
