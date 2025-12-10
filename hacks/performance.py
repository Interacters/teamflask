from flask import Blueprint, jsonify, request
from flask_restful import Api, Resource

from hacks.performances import *

performance_api = Blueprint('performance_api', __name__, url_prefix='/api/performance')
api = Api(performance_api)

class PerformanceAPI:
    
    class _Submit(Resource):
        """Submit a new performance rating"""
        def post(self):
            data = request.get_json()
            rating = data.get('rating')
            
            if not rating or rating not in [1, 2, 3, 4, 5]:
                return jsonify({'error': 'Invalid rating. Must be 1-5.'}), 400
            
            # Add the rating
            new_performance = addPerformance(rating)
            
            # Calculate average
            avg_rating = getAverageRating()
            
            # Determine status
            if rating < avg_rating:
                status = "underprepared"
                message = f"The majority felt {avg_rating}/5 prepared. You rated {rating}/5 - there's room to grow!"
            elif rating > avg_rating:
                status = "overprepared"
                message = f"Great! You rated {rating}/5 while most felt {avg_rating}/5. You're well-prepared!"
            else:
                status = "average"
                message = f"You're right on track! Most people also felt {avg_rating}/5 prepared."
            
            return jsonify({
                'your_rating': rating,
                'average_rating': avg_rating,
                'status': status,
                'message': message,
                'performance_id': new_performance['id']
            }), 200
    
    class _Read(Resource):
        """Get all performance ratings"""
        def get(self):
            return jsonify(getPerformances())
    
    class _ReadStats(Resource):
        """Get performance statistics"""
        def get(self):
            return jsonify({
                'count': countPerformances(),
                'average': getAverageRating(),
                'distribution': getRatingDistribution(),
                'most_common': getMostCommonRating()
            })
    
    class _ReadCount(Resource):
        """Get count of performance ratings"""
        def get(self):
            return jsonify({'count': countPerformances()})
    
    # Add resources to API
    api.add_resource(_Submit, '/submit', '/submit/')
    api.add_resource(_Read, '', '/')
    api.add_resource(_ReadStats, '/stats', '/stats/')
    api.add_resource(_ReadCount, '/count', '/count/')