from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from datetime import datetime
from __init__ import db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from api.jwt_authorize import token_required

# ...existing imports above...
from flask_restful import Api, Resource
from flask_cors import CORS
# ...other imports...

# Create Blueprint
media_api = Blueprint('media_api', __name__, url_prefix='/api/media')
# Allow cross-origin requests from your frontend during development:

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
    
class MediaScoreUpdateAPI(Resource):
    """Update media score - Admin only"""
    
    @token_required(["Admin"])
    def put(self, score_id):
        """Update a media score"""
        try:
            body = request.get_json()
            
            score = MediaScore.query.get(score_id)
            if not score:
                return {'message': 'Score not found'}, 404
            
            # Update fields if provided
            if body.get('username'):
                score.username = body.get('username')
            if body.get('time') is not None:
                try:
                    score.time = int(body.get('time'))
                except (ValueError, TypeError):
                    return {'message': 'Time must be an integer'}, 400
            
            db.session.commit()
            return score.read(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error updating score: {str(e)}'}, 500

class MediaScoreDeleteAPI(Resource):
    """Delete media score - Admin only"""
    
    @token_required(["Admin"])
    def delete(self, score_id):
        """Delete a media score"""
        try:
            score = MediaScore.query.get(score_id)
            if not score:
                return {'message': 'Score not found'}, 404
            
            db.session.delete(score)
            db.session.commit()
            
            return {'message': f'Score {score_id} deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error deleting score: {str(e)}'}, 500

    
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from flask import make_response
import re

# ===== ENHANCED CITATION QUALITY CHECKER =====
# Add these imports at the top of media_api.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from datetime import datetime

# Expanded credible domains with more nuance
CREDIBLE_DOMAINS = {
    # Tier 1: Academic & Scientific (9-10)
    'nature.com': 10,
    'science.org': 10,
    'sciencedirect.com': 10,
    'jstor.org': 10,
    'ncbi.nlm.nih.gov': 10,
    'pubmed.ncbi.nlm.nih.gov': 10,
    'arxiv.org': 9,
    'pnas.org': 10,
    'thelancet.com': 10,
    
    # Tier 2: Major International News (8-9)
    'bbc.com': 9,
    'bbc.co.uk': 9,
    'reuters.com': 9,
    'apnews.com': 9,
    'associatedpress.org': 9,
    'economist.com': 9,
    'foreignaffairs.com': 9,
    'propublica.org': 9,
    
    # Tier 3: Major US News (7-8)
    'nytimes.com': 8,
    'washingtonpost.com': 8,
    'wsj.com': 8,
    'npr.org': 8,
    'pbs.org': 8,
    'theguardian.com': 8,
    'theatlantic.com': 8,
    
    # Tier 4: Mainstream News (6-7)
    'cnn.com': 7,
    'cbsnews.com': 7,
    'abcnews.go.com': 7,
    'nbcnews.com': 7,
    'usatoday.com': 7,
    'time.com': 7,
    'newsweek.com': 7,
    'axios.com': 7,
    'politico.com': 7,
    'bloomberg.com': 8,
    'forbes.com': 7,
}

# Questionable or low-quality sources
QUESTIONABLE_DOMAINS = {
    'dailymail.co.uk': 4,
    'nypost.com': 5,
    'breitbart.com': 3,
    'infowars.com': 1,
    'naturalnews.com': 2,
    'beforeitsnews.com': 2,
    'bipartisanreport.com': 3,
    'occupydemocrats.com': 3,
    'thegatewaypundit.com': 2,
    'zerohedge.com': 3,
    'activistpost.com': 3,
}

# Educational institutions (automatic boost)
EDU_KEYWORDS = ['university', 'college', 'institute', 'academia', 'edu']

# Government domains
GOV_KEYWORDS = ['gov', 'senate', 'congress', 'whitehouse']

# Red flags in URLs/domains
RED_FLAGS = ['blog', 'wordpress', 'tumblr', 'blogspot', 'medium.com/~']

def check_author_credentials(author, url=None):
    """
    Check if author has credentials or appears in the content.
    Returns score adjustment (-1, 0, +1, +2)
    """
    if not author or len(str(author).strip()) < 2:
        return -1  # No author listed
    
    author_clean = str(author).lower().strip()
    
    # Check for academic credentials
    if any(cred in author_clean for cred in ['phd', 'ph.d', 'dr.', 'professor', 'prof.']):
        return +2
    
    # Check for journalistic credentials
    if any(title in author_clean for title in ['editor', 'correspondent', 'reporter', 'journalist']):
        return +1
    
    # Check if author name looks legitimate (has comma or multiple words)
    if ',' in author or len(author.split()) >= 2:
        return +1
    
    return 0

def check_url_quality(url):
    """
    Analyze URL structure for quality indicators.
    Returns score adjustment (-2 to +2)
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        score_adj = 0
        
        # Check for red flags
        if any(flag in domain or flag in path for flag in RED_FLAGS):
            score_adj -= 1
        
        # Check for news/article indicators
        if any(indicator in path for indicator in ['/news/', '/article/', '/story/', '/report/']):
            score_adj += 1
        
        # Check for opinion pieces (slightly lower credibility)
        if any(opinion in path for opinion in ['/opinion/', '/blog/', '/editorial/']):
            score_adj -= 1
        
        # Check for specific content types
        if '/press-release/' in path or '/pr/' in path:
            score_adj -= 1
        
        # Academic papers
        if any(academic in path for academic in ['/journal/', '/paper/', '/article/', '/doi/']):
            score_adj += 1
        
        return score_adj
        
    except Exception:
        return 0

def check_date_recency(date_str):
    """
    More nuanced date checking.
    Returns score adjustment (0 to +3)
    """
    if not date_str:
        return 0
    
    try:
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
        if not year_match:
            return 0
        
        year = int(year_match.group())
        current_year = datetime.now().year
        age = current_year - year
        
        # Very recent (last 2 years)
        if age <= 2:
            return +3
        # Recent (3-5 years)
        elif age <= 5:
            return +2
        # Somewhat recent (6-10 years)
        elif age <= 10:
            return +1
        # Old but potentially still relevant (11-15 years)
        elif age <= 15:
            return 0
        # Very old (15+ years) - context matters
        else:
            return -1
            
    except Exception:
        return 0

def fetch_page_indicators(url):
    """
    Fetch the actual page and look for quality indicators.
    Returns dict with various quality signals.
    """
    indicators = {
        'has_citations': False,
        'has_byline': False,
        'word_count': 0,
        'has_sources': False,
        'professional_layout': False
    }
    
    try:
        # Only fetch if it's a credible domain (avoid wasting time on junk)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for citations/references
            if soup.find(['cite', 'sup']) or soup.find(class_=re.compile(r'citation|reference|source', re.I)):
                indicators['has_citations'] = True
            
            # Check for byline
            if soup.find(class_=re.compile(r'byline|author', re.I)):
                indicators['has_byline'] = True
            
            # Estimate word count (content quality)
            text = soup.get_text()
            word_count = len(text.split())
            indicators['word_count'] = word_count
            
            # Look for source mentions
            if re.search(r'according to|sources say|cited|reported by', text, re.I):
                indicators['has_sources'] = True
                
    except Exception as e:
        print(f"Could not fetch page indicators: {e}")
    
    return indicators

def check_citation_quality_enhanced(url, author, date, source, fetch_page=False):
    """
    Enhanced quality checking with multiple factors.
    Returns score from 1-10 with detailed reasoning.
    """
    score = 5  # baseline
    reasons = []
    
    try:
        # Parse URL
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        # 1. Domain reputation (primary factor)
        if domain in CREDIBLE_DOMAINS:
            score = CREDIBLE_DOMAINS[domain]
            reasons.append(f"Known credible source ({CREDIBLE_DOMAINS[domain]}/10 base)")
        elif domain in QUESTIONABLE_DOMAINS:
            score = QUESTIONABLE_DOMAINS[domain]
            reasons.append(f"Known questionable source ({QUESTIONABLE_DOMAINS[domain]}/10 base)")
        else:
            reasons.append("Unknown domain (5/10 base)")
        
        # 2. TLD bonuses
        if domain.endswith(('.edu', '.ac.uk', '.edu.au')):
            adj = +2
            score += adj
            reasons.append(f"Educational institution (+{adj})")
        elif domain.endswith(('.gov', '.gov.uk')):
            adj = +2
            score += adj
            reasons.append(f"Government source (+{adj})")
        elif domain.endswith('.org'):
            # .org is mixed - check if it's a known credible org
            if domain not in CREDIBLE_DOMAINS:
                adj = +1
                score += adj
                reasons.append(f"Non-profit organization (+{adj})")
        
        # 3. HTTPS
        if parsed.scheme == 'https':
            adj = +1
            score += adj
            reasons.append(f"Secure connection (+{adj})")
        
        # 4. Author credentials
        author_adj = check_author_credentials(author, url)
        if author_adj != 0:
            score += author_adj
            if author_adj > 0:
                reasons.append(f"Author credentials (+{author_adj})")
            else:
                reasons.append(f"No author listed ({author_adj})")
        
        # 5. URL structure
        url_adj = check_url_quality(url)
        if url_adj != 0:
            score += url_adj
            reasons.append(f"URL quality ({url_adj:+d})")
        
        # 6. Date recency
        date_adj = check_date_recency(date)
        if date_adj != 0:
            score += date_adj
            if date_adj > 0:
                reasons.append(f"Recent publication (+{date_adj})")
            else:
                reasons.append(f"Outdated content ({date_adj})")
        
        # 7. Optional: Fetch page for deeper analysis
        if fetch_page and score >= 5:  # Only for decent sources
            indicators = fetch_page_indicators(url)
            
            if indicators['has_citations']:
                score += 1
                reasons.append("Contains citations (+1)")
            
            if indicators['word_count'] > 500:
                score += 1
                reasons.append("Substantial content (+1)")
        
        # Cap between 1-10
        final_score = min(max(score, 1), 10)
        
        return {
            'score': final_score,
            'reasons': reasons,
            'raw_score': score
        }
        
    except Exception as e:
        print(f"Error in quality check: {e}")
        return {
            'score': 5,
            'reasons': ['Error during analysis'],
            'raw_score': 5
        }

@media_api.route('/check_quality', methods=['POST', 'OPTIONS'])  # Add OPTIONS
def check_quality():
    """
    Enhanced quality checker endpoint.
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp
    
    try:
        data = request.get_json()
        
        if not data:
            resp = make_response(jsonify({'error': 'Request body is required'}), 400)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
        
        url = data.get('url', '')
        author = data.get('author', '')
        date = data.get('date', '')
        source = data.get('source', '')
        deep_check = data.get('deep_check', False)
        
        if not url:
            resp = make_response(jsonify({'error': 'URL is required'}), 400)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
        
        # Calculate enhanced quality score
        result = check_citation_quality_enhanced(url, author, date, source, fetch_page=deep_check)
        score = result['score']
        
        # Determine quality level and message
        if score >= 8:
            quality = 'high'
            message = 'Highly credible source'
        elif score >= 6:
            quality = 'medium'
            message = 'Moderately credible source'
        else:
            quality = 'low'
            message = 'Consider finding a more credible source'
        
        # Create response with CORS headers
        resp = make_response(jsonify({
            'score': score,
            'quality': quality,
            'message': message,
            'reasons': result['reasons'],
            'details': {
                'author_present': bool(author and len(author.strip()) > 2),
                'date_present': bool(date),
                'https': url.startswith('https://'),
                'raw_score': result['raw_score']
            }
        }), 200)
        
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
        
    except Exception as e:
        resp = make_response(jsonify({'error': f'Error checking quality: {str(e)}'}), 500)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

# ===== USAGE EXAMPLE =====
"""
# Basic check (fast)
POST /api/media/check_quality
{
    "url": "https://www.nature.com/articles/12345",
    "author": "Dr. Smith, PhD",
    "date": "2024",
    "source": "Nature"
}

# Deep check (slower, fetches page)
POST /api/media/check_quality
{
    "url": "https://example.com/article",
    "author": "John Doe",
    "date": "2023",
    "source": "Example News",
    "deep_check": true
}
"""

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
api.add_resource(MediaScoreUpdateAPI, '/score/update/<int:score_id>')
api.add_resource(MediaScoreDeleteAPI, '/score/delete/<int:score_id>')
# Register the media_api blueprint with the main Flask app
from __init__ import app  # Make sure you have the app object imported