from flask import Blueprint, request, current_app, g
from flask_restful import Api, Resource
import traceback
from api.jwt_authorize import token_required

from hacks.performances import *

performance_api = Blueprint('performance_api', __name__, url_prefix='/api/performance')

# API generator https://flask-restful.readthedocs.io/en/latest/api.html#id1
api = Api(performance_api)

class PerformanceAPI:
    
    class _Submit(Resource):
        """Submit a new performance rating"""
        def options(self):
            """Handle OPTIONS preflight for CORS"""
            return {}, 200
        
        @token_required()
        def post(self):
            try:
                # Get current user from token
                current_user = g.current_user
                
                data = request.get_json()
                
                if not data:
                    return {'error': 'No data provided'}, 400
                
                rating = data.get('rating')
                
                # More detailed validation
                if rating is None:
                    return {'error': 'Rating field is required'}, 400
                
                # Convert to int if it's a string
                try:
                    rating = int(rating)
                except (ValueError, TypeError):
                    return {'error': 'Rating must be a number'}, 400
                
                if rating not in [1, 2, 3, 4, 5]:
                    return {'error': 'Invalid rating. Must be 1-5.'}, 400
                
                # Add the rating with user info (atomic operation with file locking)
                new_performance = addPerformance(
                    rating=rating, 
                    user_id=current_user.id,
                    username=current_user.uid
                )
                
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
                
                return {
                    'your_rating': rating,
                    'average_rating': avg_rating,
                    'status': status,
                    'message': message,
                    'performance_id': new_performance['id'],
                    'username': current_user.uid
                }, 200
                
            except Exception as e:
                # Log the full error for debugging
                current_app.logger.error(f"Error in performance submit: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return {
                    'error': 'Internal server error',
                    'details': str(e),
                    'type': type(e).__name__
                }, 500
    
    class _Read(Resource):
        """Get all performance ratings"""
        @token_required()
        def get(self):
            try:
                return getPerformances()
            except Exception as e:
                current_app.logger.error(f"Error reading performances: {str(e)}")
                return {'error': str(e)}, 500
    
    class _ReadID(Resource):
        """Get a specific performance rating by id"""
        @token_required()
        def get(self, id):
            try:
                performance = getPerformance(id)
                if performance:
                    return performance
                return {'error': 'Performance not found'}, 404
            except Exception as e:
                current_app.logger.error(f"Error reading performance {id}: {str(e)}")
                return {'error': str(e)}, 500
    
    class _ReadUserPerformances(Resource):
        """Get all performances by a specific user"""
        @token_required()
        def get(self, user_id):
            try:
                performances = getUserPerformances(user_id)
                return performances
            except Exception as e:
                current_app.logger.error(f"Error reading user performances: {str(e)}")
                return {'error': str(e)}, 500
    
    class _ReadStats(Resource):
        """Get performance statistics"""
        def get(self):
            try:
                return {
                    'count': countPerformances(),
                    'average': getAverageRating(),
                    'distribution': getRatingDistribution(),
                    'most_common': getMostCommonRating()
                }
            except Exception as e:
                current_app.logger.error(f"Error reading stats: {str(e)}")
                return {'error': str(e)}, 500
    
    class _ReadCount(Resource):
        """Get count of performance ratings"""
        def get(self):
            try:
                count = countPerformances()
                countMsg = {'count': count}
                return countMsg
            except Exception as e:
                current_app.logger.error(f"Error counting performances: {str(e)}")
                return {'error': str(e)}, 500
    
    # building RESTapi resources/interfaces, these routes are added to Web Server
    api.add_resource(_Submit, '/submit', '/submit/')
    api.add_resource(_Read, '', '/')
    api.add_resource(_ReadID, '/<int:id>', '/<int:id>/')
    api.add_resource(_ReadUserPerformances, '/user/<int:user_id>', '/user/<int:user_id>/')
    api.add_resource(_ReadStats, '/stats', '/stats/')
    api.add_resource(_ReadCount, '/count', '/count/')