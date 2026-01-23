
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from cms_app import create_app, db
from cms_app.models import FeesRecord, FeePayment, TimetableSettings, TimetableSlot, Faculty

app = create_app()

with app.app_context():
    try:
        print("Verifying database models...")
        db.create_all()
        print("Database models verified.")
        
        print("Checking FeesRecord model...")
        fees_count = FeesRecord.query.count()
        print(f"FeesRecord count: {fees_count}")

        print("Checking Faculty model...")
        faculty_count = Faculty.query.count()
        print(f"Faculty count: {faculty_count}")

        print("Checking Timetable models...")
        ts_count = TimetableSettings.query.count()
        slot_count = TimetableSlot.query.count()
        print(f"TimetableSettings: {ts_count}, TimetableSlots: {slot_count}")
        
        print("Verification successful!")
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
