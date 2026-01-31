
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'cms.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print(f"{'ID':<5} {'Username':<20} {'Role':<15} {'Is Super Admin':<15} {'Password Hash (First 10)':<25}")
print("-" * 85)

try:
    cursor.execute("SELECT user_id, username, role, is_super_admin, password_hash FROM users")
    users = cursor.fetchall()
    for u in users:
        uid, username, role, is_super, phash = u
        phash_display = phash[:10] + "..." if phash else "None"
        print(f"{uid:<5} {username:<20} {role:<15} {str(is_super):<15} {phash_display:<25}")
except Exception as e:
    print(f"Error: {e}")

conn.close()
