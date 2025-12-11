from flask import Blueprint, request, current_app
from flask_restful import Api, Resource
import traceback

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
        
        def post(self):
            try:
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
                
                # Add the rating (atomic operation with file locking)
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
                
                return {
                    'your_rating': rating,
                    'average_rating': avg_rating,
                    'status': status,
                    'message': message,
                    'performance_id': new_performance['id']
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
    
    # getPerformances()
    class _Read(Resource):
        """Get all performance ratings"""
        def get(self):
            try:
                # Don't use jsonify() - Flask-RESTful handles JSON conversion
                return getPerformances()
            except Exception as e:
                current_app.logger.error(f"Error reading performances: {str(e)}")
                return {'error': str(e)}, 500
    
    # getPerformance(id)
    class _ReadID(Resource):
        """Get a specific performance rating by id"""
        def get(self, id):
            try:
                performance = getPerformance(id)
                if performance:
                    # Don't use jsonify() - return dict directly
                    return performance
                return {'error': 'Performance not found'}, 404
            except Exception as e:
                current_app.logger.error(f"Error reading performance {id}: {str(e)}")
                return {'error': str(e)}, 500
    
    # getPerformanceStats()
    class _ReadStats(Resource):
        """Get performance statistics"""
        def get(self):
            try:
                # Don't use jsonify() - return dict directly
                return {
                    'count': countPerformances(),
                    'average': getAverageRating(),
                    'distribution': getRatingDistribution(),
                    'most_common': getMostCommonRating()
                }
            except Exception as e:
                current_app.logger.error(f"Error reading stats: {str(e)}")
                return {'error': str(e)}, 500
    
    # countPerformances()
    class _ReadCount(Resource):
        """Get count of performance ratings"""
        def get(self):
            try:
                count = countPerformances()
                countMsg = {'count': count}
                # Don't use jsonify() - return dict directly
                return countMsg
            except Exception as e:
                current_app.logger.error(f"Error counting performances: {str(e)}")
                return {'error': str(e)}, 500
    
    # building RESTapi resources/interfaces, these routes are added to Web Server
    api.add_resource(_Submit, '/submit', '/submit/')
    api.add_resource(_Read, '', '/')
    api.add_resource(_ReadID, '/<int:id>', '/<int:id>/')
    api.add_resource(_ReadStats, '/stats', '/stats/')
    api.add_resource(_ReadCount, '/count', '/count/')

# Testing code (similar to jokes.py)
if __name__ == "__main__":
    import requests
    
    # server = "http://127.0.0.1:8001"  # run local
    server = 'https://flask.opencodingsociety.com'  # run from web
    url = server + "/api/performance"
    
    print("Testing Performance API...")
    
    # Get count of performances
    count_response = requests.get(url + "/count")
    if count_response.ok:
        count_json = count_response.json()
        print(f"Total performances: {count_json['count']}")
    
    # Submit a test rating
    test_rating = 4
    submit_response = requests.post(
        url + "/submit",
        json={'rating': test_rating}
    )
    if submit_response.ok:
        result = submit_response.json()
        print(f"\nSubmitted rating: {test_rating}")
        print(f"Average rating: {result['average_rating']}")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
    else:
        print(f"Error: {submit_response.status_code}")
        print(submit_response.text)
    
    # Get statistics
    stats_response = requests.get(url + "/stats")
    if stats_response.ok:
        stats = stats_response.json()
        print(f"\nStatistics:")
        print(f"Count: {stats['count']}")
        print(f"Average: {stats['average']}")
        print(f"Distribution: {stats['distribution']}")
        print(f"Most common: {stats['most_common']}")
    
    # Get all performances
    all_response = requests.get(url)
    if all_response.ok:
        performances = all_response.json()
        print(f"\nFirst 5 performances:")
        for perf in performances[:5]:
            print(f"  ID {perf['id']}: Rating {perf['rating']}/5 at {perf['timestamp']}")