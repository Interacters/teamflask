# model/prompt.py
from datetime import datetime
from __init__ import db

class PromptClick(db.Model):
    """
    Database model for tracking prompt clicks in the media bias game
    """
    __tablename__ = 'prompt_clicks'
    
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, nullable=False, unique=True)  # 1-5 for the 5 prompts
    clicks = db.Column(db.Integer, default=0, nullable=False)
    last_clicked = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, prompt_id, clicks=0):
        self.prompt_id = prompt_id
        self.clicks = clicks
        self.last_clicked = datetime.utcnow()
    
    def increment(self):
        """Increment the click count"""
        self.clicks += 1
        self.last_clicked = datetime.utcnow()
        db.session.commit()
        return self
    
    def read(self):
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'clicks': self.clicks,
            'last_clicked': self.last_clicked.isoformat() if self.last_clicked else None
        }
    
    @classmethod
    def get_or_create(cls, prompt_id):
        """Get existing prompt click record or create new one"""
        prompt_click = cls.query.filter_by(prompt_id=prompt_id).first()
        if not prompt_click:
            prompt_click = cls(prompt_id=prompt_id)
            db.session.add(prompt_click)
            db.session.commit()
        return prompt_click
    
    @classmethod
    def get_all_clicks(cls):
        """Return dictionary of all prompt clicks"""
        all_clicks = cls.query.all()
        return {pc.prompt_id: pc.clicks for pc in all_clicks}


def init_prompt_clicks():
    """Initialize prompt click records for prompts 1-5"""
    with db.session.begin():
        for i in range(1, 6):
            existing = PromptClick.query.filter_by(prompt_id=i).first()
            if not existing:
                prompt_click = PromptClick(prompt_id=i, clicks=0)
                db.session.add(prompt_click)
    print("✅ Initialized prompt click tracking")