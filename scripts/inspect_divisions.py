
import sqlite3
conn = sqlite3.connect('cms.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(divisions)")
cols = cursor.fetchall()
for col in cols:
    print(col)
conn.close()
