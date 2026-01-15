from cms_app import create_app, db
from cms_app.models import Announcement, AnnouncementAudience
from datetime import datetime

app = create_app()

with app.app_context():
    print(f"Current Server Time: {datetime.now()}")
    print("-" * 50)
    
    anns = Announcement.query.all()
    for a in anns:
        print(f"ID: {a.announcement_id}")
        print(f"Title: {a.title}")
        print(f"Start At: {a.start_at}")
        print(f"Is Active: {a.is_active}")
        
        audiences = [aa.role for aa in a.audiences]
        print(f"Audiences: {audiences}")
        
        # Check logic
        now = datetime.now()
        is_time = (a.start_at <= now) and ((a.end_at is None) or (a.end_at >= now))
        print(f"Visible by Time? {is_time}")
        print("-" * 50)
