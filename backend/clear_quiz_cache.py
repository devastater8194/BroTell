import sqlite3

conn = sqlite3.connect('workspace.db')
c = conn.cursor()


c.execute("DELETE FROM notes WHERE note_type = 'quiz'")
deleted = c.rowcount
c.execute("UPDATE conversations SET quiz_content = NULL")
updated = c.rowcount
conn.commit()
conn.close()

print(f"Cleared {deleted} old quiz records from notes table")
print(f"Reset quiz_content on {updated} conversations")
