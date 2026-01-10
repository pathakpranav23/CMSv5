from cms_app import create_app, db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Tables found:", tables)
    if 'course_assignments' in tables:
        print("SUCCESS: course_assignments table exists.")
    else:
        print("FAILURE: course_assignments table MISSING.")
