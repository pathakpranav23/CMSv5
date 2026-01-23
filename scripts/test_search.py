
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import or_

app = create_app()

def test_search(q):
    with app.app_context():
        print(f"--- Searching for '{q}' ---")
        query = db.session.query(Student)
        query = query.filter(
            or_(
                Student.enrollment_no.ilike(f"%{q}%"),
                Student.first_name.ilike(f"%{q}%"),
                Student.last_name.ilike(f"%{q}%"),
            )
        )
        print(f"SQL: {query}")
        results = query.limit(5).all()
        print(f"Found {len(results)} results:")
        for s in results:
            print(f"  {s.enrollment_no}: {s.first_name} {s.last_name}")

if __name__ == "__main__":
    test_search("JAGRUTI")
    test_search("NAKUM")
    test_search("5034240118")
    test_search("JAGRUTI NAKUM")
