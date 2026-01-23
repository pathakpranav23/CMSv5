
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking if 'credit_rules_json' column exists in 'exam_schemes' table...")
    try:
        # Try to query the column
        db.session.execute(text("SELECT credit_rules_json FROM exam_schemes LIMIT 1"))
        print("Column 'credit_rules_json' already exists.")
    except Exception as e:
        print("Column does not exist. Adding it now...")
        try:
            db.session.execute(text("ALTER TABLE exam_schemes ADD COLUMN credit_rules_json TEXT"))
            db.session.commit()
            print("Successfully added 'credit_rules_json' column.")
        except Exception as add_err:
            print(f"Error adding column: {add_err}")
            db.session.rollback()
