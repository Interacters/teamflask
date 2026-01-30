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

    class MultiRating(db.Model):
    """
    Multi-question rating system (5 questions, 1-5 scale each)
    Different from Performance which is a single 1-5 rating
    """
    __tablename__ = 'multirating_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Five questions, each rated 1-5
    q1 = db.Column(db.Integer, nullable=False)
    q2 = db.Column(db.Integer, nullable=False)
    q3 = db.Column(db.Integer, nullable=False)
    q4 = db.Column(db.Integer, nullable=False)
    q5 = db.Column(db.Integer, nullable=False)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('multiratings', lazy=True))
    
    def __init__(self, user_id, q1, q2, q3, q4, q5):
        self.user_id = user_id
        self.q1 = int(q1)
        self.q2 = int(q2)
        self.q3 = int(q3)
        self.q4 = int(q4)
        self.q5 = int(q5)
    
    def create(self):
        db.session.add(self)
        db.session.commit()
        return self
    
    def read(self):
        """Return rating data with username from related User"""
        username = None
        if self.user:
            username = self.user.uid
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": username,
            "q1": self.q1,
            "q2": self.q2,
            "q3": self.q3,
            "q4": self.q4,
            "q5": self.q5,
            "average": round((self.q1 + self.q2 + self.q3 + self.q4 + self.q5) / 5, 2),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def get_all(cls):
        """Get all multiratings"""
        ratings = cls.query.order_by(cls.timestamp.desc()).all()
        return [r.read() for r in ratings]
    
    @classmethod
    def get_by_user(cls, user_id):
        """Get all multiratings for a specific user"""
        ratings = cls.query.filter_by(user_id=user_id).order_by(cls.timestamp.desc()).all()
        return [r.read() for r in ratings]
    
    @classmethod
    def get_averages(cls):
        """Calculate class average for each question"""
        all_ratings = cls.query.all()
        
        if not all_ratings:
            return {
                'q1': {'average': 0, 'total': 0},
                'q2': {'average': 0, 'total': 0},
                'q3': {'average': 0, 'total': 0},
                'q4': {'average': 0, 'total': 0},
                'q5': {'average': 0, 'total': 0}
            }
        
        total = len(all_ratings)
        
        return {
            'q1': {
                'average': round(sum(r.q1 for r in all_ratings) / total, 2),
                'total': total
            },
            'q2': {
                'average': round(sum(r.q2 for r in all_ratings) / total, 2),
                'total': total
            },
            'q3': {
                'average': round(sum(r.q3 for r in all_ratings) / total, 2),
                'total': total
            },
            'q4': {
                'average': round(sum(r.q4 for r in all_ratings) / total, 2),
                'total': total
            },
            'q5': {
                'average': round(sum(r.q5 for r in all_ratings) / total, 2),
                'total': total
            }
        }