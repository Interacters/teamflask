from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from datetime import datetime
from __init__ import db
from model.media import MediaScore, MediaPerson
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

# ...existing imports above...
from flask_restful import Api, Resource
from flask_cors import CORS
# ...other imports...

# Create Blueprint
media_api = Blueprint('media_api', __name__, url_prefix='/api/media')
# Allow cross-origin requests from your frontend during development:
CORS(media_api, resources={r"/*": {"origins": "http://localhost:4600"}})

api = Api(media_api)

Base = declarative_base()

# Media Score Model
class MediaScore(db.Model):
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

# Simple Person Model (for name storage without authentication)
class MediaPerson(db.Model):
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


class MediaPersonAPI(Resource):
    """Simple name registration without authentication"""
    
    def post(self):
        """Register a person with just their name"""
        body = request.get_json()
        
        if not body:
            return {'message': 'Request body is required'}, 400
        
        name = body.get('name')
        if not name or len(name.strip()) < 2:
            return {'message': 'Name is required and must be at least 2 characters'}, 400
        
        name = name.strip()
        
        # Check if person already exists
        existing_person = MediaPerson.query.filter_by(name=name).first()
        if existing_person:
            return existing_person.read(), 200
        
        # Create new person
        person = MediaPerson(name=name)
        created_person = person.create()
        
        if not created_person:
            return {'message': 'Failed to register name'}, 500
        
        return created_person.read(), 201
    
    def get(self):
        """Get person by name (query parameter)"""
        name = request.args.get('name')
        
        if not name:
            return {'message': 'Name parameter is required'}, 400
        
        person = MediaPerson.query.filter_by(name=name).first()
        
        if not person:
            return {'message': 'Person not found'}, 404
        
        return person.read(), 200


class MediaScoreAPI(Resource):
    """Submit and retrieve media bias game scores"""
    
    def post(self, username=None, time=None):
        """
        Submit a score. Supports two formats:
        1. JSON body: {"user": "username", "time": 123}
        2. Path parameters: /api/media/score/username/123
        """
        # Try to get data from path parameters first
        if username and time:
            try:
                time = int(time)
            except ValueError:
                return {'message': 'Time must be an integer'}, 400
        else:
            # Try to get data from JSON body
            body = request.get_json()
            
            if not body:
                return {'message': 'Request body is required or use path parameters'}, 400
            
            username = body.get('user') or body.get('username')
            time = body.get('time')
            
            if not username:
                return {'message': 'Username is required'}, 400
            
            if not time:
                return {'message': 'Time is required'}, 400
            
            try:
                time = int(time)
            except (ValueError, TypeError):
                return {'message': 'Time must be an integer (seconds)'}, 400
        
        # Create score entry
        score = MediaScore(username=username, time=time)
        created_score = score.create()
        
        if not created_score:
            return {'message': 'Failed to save score'}, 500
        
        return created_score.read(), 201


class MediaLeaderboardAPI(Resource):
    """Get leaderboard for media bias game"""
    
    def get(self):
        """Get top scores sorted by time (ascending - fastest times first)"""
        limit = request.args.get('limit', 50, type=int)
        
        # Get best (minimum) time for each username using subquery
        from sqlalchemy import func
        
        # Subquery to find minimum time per username
        subquery = db.session.query(
            MediaScore.username,
            func.min(MediaScore.time).label('best_time')
        ).group_by(MediaScore.username).subquery()
        
        # Join to get the full record with the best time
        # This gets the earliest entry with the best time for each user
        scores = db.session.query(MediaScore).join(
            subquery,
            db.and_(
                MediaScore.username == subquery.c.username,
                MediaScore.time == subquery.c.best_time
            )
        ).order_by(MediaScore.time.asc()).limit(limit).all()
        
        # Format as leaderboard with ranks
        leaderboard = []
        for rank, score in enumerate(scores, start=1):
            entry = score.read()
            entry['rank'] = rank
            leaderboard.append(entry)
        
        return leaderboard, 200
    
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from flask import make_response

@media_api.route('/fetch_meta')
def fetch_meta():
    target = request.args.get('url')
    if not target:
        return jsonify({'error': 'missing url'}), 400

    def parse_html(html_text, target_url):
        soup = BeautifulSoup(html_text, 'html.parser')

        def meta_content(name=None, prop=None):
            if name:
                tag = soup.find('meta', attrs={'name': name})
                if tag and tag.get('content'):
                    return tag['content'].strip()
            if prop:
                tag = soup.find('meta', attrs={'property': prop})
                if tag and tag.get('content'):
                    return tag['content'].strip()
            return None

        title = meta_content(None, 'og:title') or (soup.title.string.strip() if soup.title else None) or meta_content('twitter:title')
        author = meta_content('author') or meta_content(None, 'article:author') or meta_content('byline')
        published = meta_content(None, 'article:published_time') or meta_content('date') or meta_content('pubdate') or meta_content(None, 'og:updated_time')
        site = meta_content(None, 'og:site_name') or (urlparse(target_url).hostname.replace('www.', ''))
        canon = soup.find('link', rel='canonical')
        canon_url = urljoin(target_url, canon['href']) if canon and canon.get('href') else target_url

        return {
            'title': title,
            'author': author,
            'published': published,
            'site': site,
            'url': canon_url
        }

    try:
        # Try direct fetch first
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(target, headers=headers, timeout=12)
        r.raise_for_status()
        result = parse_html(r.text, target)

    except requests.exceptions.RequestException:
        # Fallback to AllOrigins (encode URL safely)
        try:
            from urllib.parse import quote_plus
            encoded_url = quote_plus(target)
            allorigins_url = f"https://api.allorigins.win/get?url={encoded_url}"
            r = requests.get(allorigins_url, timeout=12)
            r.raise_for_status()
            data = r.json()
            html_text = data.get('contents', '')
            result = parse_html(html_text, target)
        except Exception as e:
            return jsonify({'error': 'fetch_failed', 'detail': str(e)}), 502

    resp = make_response(jsonify(result), 200)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

# Register endpoints
api.add_resource(MediaPersonAPI, '/person/get')  # POST to register, GET with ?name=X to retrieve
api.add_resource(MediaScoreAPI, 
                 '/score',  # POST with JSON body
                 '/score/<string:username>/<int:time>')  # POST with path params
api.add_resource(MediaLeaderboardAPI, 
                 '/leaderboard',  # New dedicated leaderboard endpoint
                 '/')  # Also accessible at /api/media/ for backward compatibility

# Register the media_api blueprint with the main Flask app
from __init__ import app  # Make sure you have the app object imported
