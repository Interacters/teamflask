from __init__ import db
from datetime import datetime

class Performance(db.Model):
    __tablename__ = 'performance_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, rating):
        self.rating = rating
    
    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }