
from cms_app import create_app, db
from cms_app.models import SystemMessage
from datetime import datetime, timezone

app = create_app()
with app.app_context():
    # Create a dummy message with naive start_date (simulating existing data)
    msg = SystemMessage(title="Test", content="Test", start_date=datetime(2023, 1, 1, 12, 0, 0)) # Naive
    db.session.add(msg)
    db.session.commit()
    
    try:
        now = datetime.now(timezone.utc) # Aware
        print(f"Now (Aware): {now}")
        
        # This query mimics __init__.py
        msgs = db.session.query(SystemMessage).filter(
            SystemMessage.start_date <= now
        ).all()
        print(f"Found messages: {len(msgs)}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        db.session.delete(msg)
        db.session.commit()
