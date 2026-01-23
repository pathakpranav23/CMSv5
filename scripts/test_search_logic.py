
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select, or_

app = create_app()

def test_search(q):
    print(f"\n--- Testing search for query: '{q}' ---")
    with app.app_context():
        # Replicate logic from main/routes.py
        query = select(Student)
        if q:
            query = query.filter(
                or_(
                    Student.enrollment_no.ilike(f"%{q}%"),
                    Student.first_name.ilike(f"%{q}%"),
                    Student.last_name.ilike(f"%{q}%"),
                )
            )
        
        # Add debug: print SQL
        print("Generated SQL:")
        print(query)
        
        rows = db.session.execute(query.limit(10)).scalars().all()
        print(f"Found {len(rows)} results:")
        for s in rows:
            print(f"  {s.enrollment_no}: {s.first_name} {s.last_name} (DB cols: student_name={s.first_name}, surname={s.last_name})")

if __name__ == "__main__":
    # Test with a known name from previous output
    test_search("JAGRUTI")
    test_search("NAKUM")
    test_search("5034240118")
    test_search("NonExistent")
