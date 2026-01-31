import sys
import os
import sqlite3

# Add the parent directory to sys.path so we can import from cms_app if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'cms.db')

def add_column_if_not_exists(cursor, table, column, definition):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"Added column '{column}' to table '{table}'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column '{column}' already exists in table '{table}'.")
        else:
            print(f"Error adding column '{column}' to '{table}': {e}")

def create_table_if_not_exists(cursor, table_name, create_sql):
    try:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if cursor.fetchone():
            print(f"Table '{table_name}' already exists.")
        else:
            cursor.execute(create_sql)
            print(f"Created table '{table_name}'.")
    except Exception as e:
        print(f"Error creating table '{table_name}': {e}")

def main():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create SystemMessage table
    create_table_if_not_exists(cursor, "system_messages", """
        CREATE TABLE system_messages (
            message_id INTEGER PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            message_type VARCHAR(32) DEFAULT 'info',
            start_date DATETIME,
            end_date DATETIME,
            is_active BOOLEAN DEFAULT 1,
            target_role VARCHAR(32) DEFAULT 'all',
            target_trust_id INTEGER
        )
    """)

    # 2. Create SystemConfig table
    create_table_if_not_exists(cursor, "system_config", """
        CREATE TABLE system_config (
            config_key VARCHAR(64) PRIMARY KEY,
            config_value TEXT,
            description VARCHAR(255)
        )
    """)

    # 3. Add columns to Trusts
    add_column_if_not_exists(cursor, "trusts", "is_active", "BOOLEAN DEFAULT 1")
    add_column_if_not_exists(cursor, "trusts", "subscription_plan", "VARCHAR(32) DEFAULT 'basic'")

    # 4. Add columns to Institutes
    add_column_if_not_exists(cursor, "institutes", "is_active", "BOOLEAN DEFAULT 1")

    # 5. Add columns to Users
    add_column_if_not_exists(cursor, "users", "is_super_admin", "BOOLEAN DEFAULT 0")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    main()
