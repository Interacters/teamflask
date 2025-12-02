from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(10), nullable=False)  # "happy" or "sad"
