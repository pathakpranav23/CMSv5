
import sys
import os
from sqlalchemy import text, inspect

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db

def fix_student_schema():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('students')]
        print(f"Current 'students' columns: {columns}")

        # Columns to check and add
        new_columns = {
            'gender': 'VARCHAR(16)',
            'photo_url': 'VARCHAR(255)',
            'permanent_address': 'VARCHAR(255)',
            'medium_tag': 'VARCHAR(32)',
            'current_semester': 'INTEGER'
        }

        with db.engine.connect() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    print(f"Adding missing column: {col_name} ({col_type})")
                    try:
                        conn.execute(text(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"  - Added {col_name}")
                    except Exception as e:
                        print(f"  - Failed to add {col_name}: {e}")
                else:
                    print(f"Column '{col_name}' already exists.")
            
        print("Schema update check completed.")

if __name__ == "__main__":
    fix_student_schema()
