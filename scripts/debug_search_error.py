
import sys
import os
from sqlalchemy import select, or_, func, inspect

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Student, Program

def debug_search():
    app = create_app()
    with app.app_context():
        print("--- Debugging Search Query ---")
        
        # 1. Check Schema
        try:
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('students')]
            print(f"Table 'students' columns: {columns}")
            if 'medium_tag' not in columns:
                print("CRITICAL: 'medium_tag' column is MISSING in database!")
            else:
                print("OK: 'medium_tag' column exists.")
        except Exception as e:
            print(f"Error inspecting schema: {e}")

        try:
            # Simulate the query logic from routes.py
            q = "test"
            
            # Test 1: Basic Select
            print("1. Testing basic select count...")
            count = db.session.scalar(select(func.count()).select_from(Student))
            print(f"   Success. Count: {count}")

            # Test 2: Filter by medium (new column)
            print("2. Testing medium_tag column access...")
            try:
                # Just try to filter by it
                stmt = select(Student).filter(Student.medium_tag == 'English').limit(1)
                db.session.execute(stmt).all()
                print("   Success. medium_tag column exists and is queryable.")
            except Exception as e:
                print(f"   FAIL. medium_tag column issue: {e}")
            
            # Test 3: Full Search Query (Mocking params)
            print("3. Testing full search logic...")
            
            query = select(Student)
            # Apply medium filter
            query = query.filter(Student.medium_tag == 'English')
            
            # Apply text search
            query = query.filter(
                or_(
                    Student.enrollment_no.ilike(f"%{q}%"),
                    Student.first_name.ilike(f"%{q}%"),
                    Student.last_name.ilike(f"%{q}%"),
                    func.concat(Student.last_name, ' ', Student.first_name).ilike(f"%{q}%"),
                    func.concat(Student.first_name, ' ', Student.last_name).ilike(f"%{q}%")
                )
            )
            
            results = db.session.execute(query.limit(5)).scalars().all()
            print(f"   Success. Found {len(results)} results.")
            
            print("--- DEBUGGING COMPLETE ---")

        except Exception as e:
            print("\n!!! CRITICAL ERROR DURING DEBUGGING !!!")
            print(e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_search()
