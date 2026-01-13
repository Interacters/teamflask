# scripts/import_performances.py
"""
One-time import script to migrate existing instance/data/performances.json into the new DB table.
Usage:
    python3 scripts/import_performances.py
"""
import os
import json
from datetime import datetime
from __init__ import app, db

JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'data', 'performances.json')

def iso_to_dt(s):
    if not s:
        return None
    try:
        # Python 3.11: fromisoformat handles standard ISO strings
        return datetime.fromisoformat(s)
    except Exception:
        # fallback common format
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
        except Exception:
            return None

def import_performances():
    if not os.path.exists(JSON_PATH):
        print("performances.json not found at", JSON_PATH)
        return

    with app.app_context():
        from hacks.performance import Performance
        from model.user import User

        with open(JSON_PATH, 'r', encoding='utf-8') as fh:
            try:
                data = json.load(fh)
            except Exception as e:
                print("Error parsing JSON:", e)
                return

        inserted = 0
        for entry in data:
            rating = entry.get('rating')
            user_id = entry.get('user_id')
            username = entry.get('username') or entry.get('user') or None
            ts = entry.get('timestamp')

            # Resolve username -> user_id if possible
            resolved_user_id = None
            if username:
                u = User.query.filter_by(_uid=username).first()
                if u:
                    resolved_user_id = u.id

            # If JSON included numeric user_id and no resolution, try to confirm it exists
            if resolved_user_id is None and user_id is not None:
                exists = User.query.get(user_id)
                if exists:
                    resolved_user_id = user_id
                else:
                    # leave resolved_user_id as None, keep username if present
                    pass

            timestamp = iso_to_dt(ts) if ts else None

            perf = Performance(rating=rating, user_id=resolved_user_id, username=username, timestamp=timestamp)
            db.session.add(perf)
            inserted += 1

        db.session.commit()
        print(f"Inserted {inserted} performances into DB.")


if __name__ == '__main__':
    import_performances()