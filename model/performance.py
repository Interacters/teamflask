# model/performance.py
from datetime import datetime
from __init__ import db

class Performance(db.Model):
    """
    Database-backed Performance record that replaces instance/data/performances.json
    """
    __tablename__ = 'performances'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Made required
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # relationship to user is string-named to avoid import cycles
    user = db.relationship('User', backref=db.backref('performances', lazy=True))

    def __init__(self, rating, user_id, timestamp=None):
        self.rating = int(rating)
        self.user_id = user_id
        self.timestamp = timestamp if timestamp else datetime.utcnow()

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return None

    def read(self):
        """Return performance data with username from related User"""
        username = None
        if self.user:
            username = self.user.uid
        
        return {
            "id": self.id,
            "rating": self.rating,
            "user_id": self.user_id,
            "username": username,  # Fetched from relationship
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    @classmethod
    def list_all(cls, limit=1000):
        return cls.query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def list_for_user_id(cls, user_id, limit=1000):
        return cls.query.filter_by(user_id=user_id).order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def average_for_user_id(cls, user_id):
        from sqlalchemy import func
        avg = db.session.query(func.avg(cls.rating)).filter(cls.user_id == user_id).scalar()
        return float(round(avg, 1)) if avg is not None else None

    @classmethod
    def count_all(cls):
        return cls.query.count()


# Backwards compatibility helper
try:
    from hacks.performance import performance_api  # type: ignore
except Exception:
    performance_api = None