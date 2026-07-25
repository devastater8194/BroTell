import sqlite3

conn = sqlite3.connect('workspace.db')
c = conn.cursor()

c.execute("""
    DELETE FROM notes 
    WHERE note_type = 'quiz' 
    AND id NOT IN (
        SELECT id FROM notes 
        WHERE note_type = 'quiz' 
        GROUP BY user_id, video_id 
        ORDER BY created_at DESC
    )
""")
deleted = c.rowcount
conn.commit()
conn.close()

print(f"Deleted {deleted} duplicate quiz records from notes table")
