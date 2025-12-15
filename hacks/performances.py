import json
import os
import fcntl
from datetime import datetime
from flask import current_app

def get_performances_file():
    """Get the path to performances.json file"""
    data_folder = current_app.config['DATA_FOLDER']
    return os.path.join(data_folder, 'performances.json')

def _read_performances_file():
    """Read performances from JSON file with shared lock"""
    PERFORMANCES_FILE = get_performances_file()
    if not os.path.exists(PERFORMANCES_FILE):
        return []
    with open(PERFORMANCES_FILE, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except Exception:
            data = []
        fcntl.flock(f, fcntl.LOCK_UN)
    return data

def _write_performances_file(data):
    """Write performances to JSON file with exclusive lock"""
    PERFORMANCES_FILE = get_performances_file()
    with open(PERFORMANCES_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f)
        fcntl.flock(f, fcntl.LOCK_UN)

def initPerformances():
    """Initialize performances file if it doesn't exist"""
    PERFORMANCES_FILE = get_performances_file()
    # Only initialize if file does not exist
    if os.path.exists(PERFORMANCES_FILE):
        return
    # Start with empty list
    _write_performances_file([])

def getPerformances():
    """Get all performance ratings"""
    return _read_performances_file()

def getPerformance(id):
    """Get a specific performance rating by id"""
    performances = _read_performances_file()
    if id < len(performances):
        return performances[id]
    return None

def countPerformances():
    """Get count of all performance ratings"""
    performances = _read_performances_file()
    return len(performances)

def getAverageRating():
    """Calculate the average rating"""
    performances = _read_performances_file()
    if not performances:
        return 3.0  # Default middle value
    
    total = sum(p['rating'] for p in performances)
    return round(total / len(performances), 1)

def addPerformance(rating, user_id=None, username=None):
    """Add a new performance rating with user information"""
    PERFORMANCES_FILE = get_performances_file()
    
    # Ensure file exists before trying to open in r+ mode
    if not os.path.exists(PERFORMANCES_FILE):
        _write_performances_file([])
    
    with open(PERFORMANCES_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0)
            content = f.read()
            if content:
                performances = json.loads(content)
            else:
                performances = []
        except (json.JSONDecodeError, Exception):
            performances = []
        
        # Create new performance entry with user info
        new_id = len(performances)
        new_performance = {
            'id': new_id,
            'rating': rating,
            'user_id': user_id,
            'username': username or 'Guest',
            'timestamp': datetime.utcnow().isoformat()
        }
        performances.append(new_performance)
        
        # Write back to file
        f.seek(0)
        json.dump(performances, f, indent=2)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    
    return new_performance

def getRatingDistribution():
    """Get distribution of ratings (1-5)"""
    performances = _read_performances_file()
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    for perf in performances:
        rating = perf['rating']
        if rating in distribution:
            distribution[rating] += 1
    
    return distribution

def getMostCommonRating():
    """Get the most frequently selected rating"""
    distribution = getRatingDistribution()
    if not distribution or sum(distribution.values()) == 0:
        return 3
    
    return max(distribution, key=distribution.get)

def getUserPerformances(user_id):
    """Get all performances by a specific user"""
    performances = _read_performances_file()
    return [p for p in performances if p.get('user_id') == user_id]

def printPerformance(performance):
    """Print a performance rating (for debugging)"""
    print(
        performance['id'], 
        f"Rating: {performance['rating']}/5",
        f"User: {performance.get('username', 'Unknown')}",
        "\nTimestamp:", performance['timestamp']
    )