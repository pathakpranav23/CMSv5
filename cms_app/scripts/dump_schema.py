
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'cms.db')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'schema_dump.txt')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    for name, sql in tables:
        f.write(f"--- Table: {name} ---\n")
        f.write(sql if sql else "NO SQL")
        f.write("\n\n")

conn.close()
print(f"Schema dumped to {OUTPUT_PATH}")
