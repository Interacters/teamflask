# model/media.py
from datetime import datetime
from __init__ import db

class MediaScore(db.Model):
    """
    Database model for media bias game scores
    """
    __tablename__ = 'media_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    time = db.Column(db.Integer, nullable=False)  # Time in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, username, time):
        self.username = username
        self.time = time
    
    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            print(f"Error creating media score: {e}")
            return None
    
    def read(self):
        return {
            'id': self.id,
            'username': self.username,
            'time': self.time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def list_all(cls, limit=1000):
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def list_for_username(cls, username, limit=1000):
        return cls.query.filter_by(username=username).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_best_time(cls, username):
        """Get the best (minimum) time for a user"""
        from sqlalchemy import func
        best = db.session.query(func.min(cls.time)).filter(cls.username == username).scalar()
        return best if best is not None else None


class MediaPerson(db.Model):
    """
    Simple person model for media game (name storage without full authentication)
    """
    __tablename__ = 'media_persons'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, name):
        self.name = name
    
    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            print(f"Error creating media person: {e}")
            return None
    
    def read(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }