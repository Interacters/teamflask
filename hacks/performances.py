# hacks/performances.py
# Reimplemented to use the database (model.performance.Performance) instead of JSON file.
from datetime import datetime
from flask import current_app
from __init__ import db

def initPerformances():
    """
    Ensure that the performances table exists. This function is a no-op if tables already exist;
    it calls db.create_all() to be safe.
    """
    with current_app.app_context():
        # Import here to avoid cycles at module import time
        from hacks.performance import Performance
        db.create_all()
        return True


def getPerformances():
    """Return a list of all performances as dictionaries (most recent first)."""
    from hacks.performance import Performance
    items = Performance.list_all(limit=1000)
    return [p.read() for p in items]


def getPerformance(id):
    """Get a specific performance by primary key id; returns dict or None."""
    from hacks.performance import Performance
    p = Performance.query.get(id)
    return p.read() if p else None


def countPerformances():
    """Return an integer count of performance rows."""
    from hacks.performance import Performance
    return Performance.count_all()


def getAverageRating():
    """Compute average rating across all performances. Default to 3.0 if none."""
    from hacks.performance import Performance
    from sqlalchemy import func
    avg = db.session.query(func.avg(Performance.rating)).scalar()
    if avg is None:
        return 3.0
    return round(float(avg), 1)


def addPerformance(rating, user_id=None, username=None):
    """
    Add a new performance record into the DB.
    Returns a dict matching the old JSON entry structure (id, rating, user_id, username, timestamp)
    """
    from hacks.performance import Performance
    # Normalize inputs
    try:
        rating = int(rating)
    except Exception:
        raise ValueError("rating must be an integer")

    # Create and persist
    perf = Performance(rating=rating, user_id=user_id, username=username, timestamp=datetime.utcnow())
    perf.create()
    return perf.read()


def getRatingDistribution():
    """
    Return a dict with counts for ratings 1..5
    """
    from hacks.performance import Performance
    from sqlalchemy import func
    # build base dict
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    # aggregate
    rows = db.session.query(Performance.rating, func.count(Performance.rating)).group_by(Performance.rating).all()
    for rating, count in rows:
        if rating in distribution:
            distribution[int(rating)] = int(count)
    return distribution


def getMostCommonRating():
    """
    Return the rating (1-5) that occurs most often. If tie or none, returns 3 as fallback.
    """
    dist = getRatingDistribution()
    total = sum(dist.values())
    if total == 0:
        return 3
    # max key by value
    return max(dist, key=dist.get)


def getUserPerformances(user_id):
    """Return list of performance dicts for a given user_id (int)."""
    from hacks.performance import Performance
    items = Performance.list_for_user_id(user_id, limit=1000)
    return [p.read() for p in items]


def printPerformance(performance):
    """
    Print a performance dict or a SQLAlchemy Performance.read() dict.
    Kept for compatibility with existing debug usage.
    """
    if performance is None:
        print("No performance provided")
        return
    # If it's a model instance, convert
    try:
        # duck-type check for dict
        if isinstance(performance, dict):
            perf = performance
        else:
            # assume SQLAlchemy model with read()
            perf = performance.read()
    except Exception:
        perf = performance
    print(
        perf.get('id'),
        f"Rating: {perf.get('rating')}/5",
        f"User: {perf.get('username', 'Unknown')}",
        "\nTimestamp:", perf.get('timestamp')
    )