from flask import Blueprint, request, jsonify
from model.performance import Performance, db
from sqlalchemy import func

performance_api = Blueprint('performance_api', __name__, url_prefix='/api/performance')

@performance_api.route('/submit', methods=['POST'])
def submit_rating():
    data = request.get_json()
    rating = data.get('rating')
    
    if not rating or rating not in [1, 2, 3, 4, 5]:
        return jsonify({'error': 'Invalid rating'}), 400
    
    # Save rating
    new_rating = Performance(rating=rating)
    db.session.add(new_rating)
    db.session.commit()
    
    # Calculate average
    avg = db.session.query(func.avg(Performance.rating)).scalar()
    avg_rounded = round(avg) if avg else 3
    
    # Determine feedback
    if rating < avg_rounded:
        status = "underprepared"
        message = f"The majority felt {avg_rounded}/5 prepared. You rated {rating}/5 - you're underprepared."
        resources = [
            "📚 Review the study guide",
            "🎯 Practice more examples", 
            "💡 Watch tutorial videos"
        ]
    elif rating > avg_rounded:
        status = "overprepared"
        message = f"Great! You rated {rating}/5 while most felt {avg_rounded}/5. You're well-prepared!"
        resources = [
            "🌟 Help others who need it",
            "🚀 Try advanced challenges",
            "💪 Keep up the great work"
        ]
    else:
        status = "average"
        message = f"You're right on track! Most people also felt {avg_rounded}/5 prepared."
        resources = [
            "✅ Continue your current pace",
            "📖 Review any weak areas",
            "🎯 Stay consistent"
        ]
    
    return jsonify({
        'your_rating': rating,
        'average_rating': avg_rounded,
        'status': status,
        'message': message,
        'resources': resources
    }), 200