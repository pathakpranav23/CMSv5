
from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select

app = create_app()

def check_students():
    with app.app_context():
        # Check Srushti
        srushti = db.session.execute(
            select(Student).filter(Student.first_name.ilike('%Srushti%'))
        ).scalars().all()
        
        print("\n--- DB Search: Srushti ---")
        if srushti:
            for s in srushti:
                print(f"Name: {s.full_name}, Roll: {s.roll_no}, Enr: {s.enrollment_no}, Sem: {s.current_semester}")
        else:
            print("Srushti not found in DB.")

        # Check Mahir
        mahir = db.session.execute(
            select(Student).filter(Student.first_name.ilike('%Mahir%'))
        ).scalars().all()
        
        print("\n--- DB Search: Mahir ---")
        if mahir:
            for s in mahir:
                print(f"Name: {s.full_name}, Roll: {s.roll_no}, Enr: {s.enrollment_no}, Sem: {s.current_semester}")
        else:
            print("Mahir not found in DB.")

if __name__ == "__main__":
    check_students()
