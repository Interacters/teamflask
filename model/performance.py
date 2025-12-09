from __init__ import db
from datetime import datetime

class Performance(db.Model):
    __tablename__ = 'performance_survey'
    
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)