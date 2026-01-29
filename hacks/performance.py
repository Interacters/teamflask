
# This handles individual rating submissions

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from model.performance import MultiRating

@performance_api.route('/multirating/submit', methods=['POST'])
@login_required

def submit_multirating():
    """
    Submit a multi-question rating survey
    
    Expected JSON body:
    {
        "q1": 3,
        "q2": 4,
        "q3": 5,
        "q4": 2,
        "q5": 4
    }
    """
    try:
        data = request.get_json()
        
        # Validate all questions
        required = ['q1', 'q2', 'q3', 'q4', 'q5']
        for q in required:
            if q not in data:
                return jsonify({'error': f'Missing {q}'}), 400
            if not isinstance(data[q], int) or data[q] < 1 or data[q] > 5:
                return jsonify({'error': f'{q} must be 1-5'}), 400
        
        # Create new rating
        rating = MultiRating(
            user_id=current_user.id,
            username=current_user.name,
            q1=data['q1'],
            q2=data['q2'],
            q3=data['q3'],
            q4=data['q4'],
            q5=data['q5']
        )
        
        rating.create()
        
        return jsonify({
            'message': 'Rating submitted successfully',
            'rating': rating.read()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@performance_api.route('/multirating/stats', methods=['GET'])
def get_multirating_stats():
    """
    Get class averages for all 5 questions
    
    Returns:
    {
        "q1": {"average": 3.5, "total": 20},
        "q2": {"average": 4.1, "total": 20},
        ...
    }
    """
    try:
        stats = MultiRating.get_averages()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # ADD THIS TO THE BOTTOM OF: hacks/performance.py
# (After the existing PerformanceAPI class)

class MultiRatingAPI:
    """
    New API for multi-question ratings (5 questions, 1-5 each)
    Separate from the single-rating Performance API
    """
    
    class _Submit(Resource):
        """Submit a multi-question rating"""
        def options(self):
            """Handle OPTIONS preflight for CORS"""
            return {}, 200
        
        @token_required()
        def post(self):
            try:
                from model.performance import MultiRating
                
                current_user = g.current_user
                data = request.get_json()
                
                if not data:
                    return {'error': 'No data provided'}, 400
                
                # Validate all 5 questions
                required = ['q1', 'q2', 'q3', 'q4', 'q5']
                for q in required:
                    if q not in data:
                        return {'error': f'Missing {q}'}, 400
                    
                    try:
                        rating = int(data[q])
                        if rating not in [1, 2, 3, 4, 5]:
                            return {'error': f'{q} must be 1-5'}, 400
                    except (ValueError, TypeError):
                        return {'error': f'{q} must be a number'}, 400
                
                # Create new multirating
                multirating = MultiRating(
                    user_id=current_user.id,
                    q1=data['q1'],
                    q2=data['q2'],
                    q3=data['q3'],
                    q4=data['q4'],
                    q5=data['q5']
                )
                
                multirating.create()
                
                return {
                    'message': 'Ratings submitted successfully',
                    'rating': multirating.read()
                }, 200
                
            except Exception as e:
                current_app.logger.error(f"Error in multirating submit: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return {'error': str(e)}, 500
    
    class _Stats(Resource):
        """Get class averages for all 5 questions"""
        def get(self):
            try:
                from model.performance import MultiRating
                stats = MultiRating.get_averages()
                return stats, 200
            except Exception as e:
                current_app.logger.error(f"Error getting multirating stats: {str(e)}")
                return {'error': str(e)}, 500
    
    class _AllResponses(Resource):
        """Get all multirating responses (admin only)"""
        @token_required(["Admin"])
        def get(self):
            try:
                from model.performance import MultiRating
                responses = MultiRating.get_all()
                return responses, 200
            except Exception as e:
                current_app.logger.error(f"Error getting all multiratings: {str(e)}")
                return {'error': str(e)}, 500
    
    class _UserResponses(Resource):
        """Get multiratings for a specific user (admin only)"""
        @token_required(["Admin"])
        def get(self, user_id):
            try:
                from model.performance import MultiRating
                responses = MultiRating.get_by_user(user_id)
                return responses, 200
            except Exception as e:
                current_app.logger.error(f"Error getting user multiratings: {str(e)}")
                return {'error': str(e)}, 500
    
    # Add the new routes to the API
    api.add_resource(_Submit, '/multirating/submit', '/multirating/submit/')
    api.add_resource(_Stats, '/multirating/stats', '/multirating/stats/')
    api.add_resource(_AllResponses, '/multirating/responses', '/multirating/responses/')
    api.add_resource(_UserResponses, '/multirating/user/<int:user_id>', '/multirating/user/<int:user_id>/')