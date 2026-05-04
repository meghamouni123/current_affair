import psycopg2
try:
    conn = psycopg2.connect("postgresql://ca_portal_db_68b1_user:ZRjyNxKDO6PW8gwP8pqvri5SqgZUxFMD@dpg-d790j0nfte5s739cvlug-a.virginia-postgres.render.com/ca_portal_db_68b1")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM exam_ca_articles")
    print("Render DB alive. Total rows:", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("Render DB error:", e)
