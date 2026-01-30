from flask import Blueprint, request, jsonify, g
from api.jwt_authorize import token_required
from model.performance import Performance
from hacks.performances import (
    getPerformances,
    countPerformances,
    getAverageRating,
    getRatingDistribution,
    getMostCommonRating
)

multirating_api = Blueprint('multirating_api', __name__, url_prefix='/api/multirating')

@multirating_api.route('/stats', methods=['GET'])
def get_stats():
    """
    Get statistics for all performance ratings
    Public endpoint - no authentication required
    """
    try:
        # Use your existing helper functions
        total = countPerformances()
        average = getAverageRating()
        distribution = getRatingDistribution()
        
        # Convert distribution keys to strings for JSON
        distribution_str = {str(k): v for k, v in distribution.items()}
        
        return jsonify({
            'total_responses': total,
            'average_rating': average,
            'rating_distribution': distribution_str,
            'most_common': getMostCommonRating()
        }), 200
        
    except Exception as e:
        print(f"❌ Error in multirating get_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to fetch stats',
            'details': str(e)
        }), 500

@multirating_api.route('/responses', methods=['GET'])
@token_required(['Admin'])
def get_responses():
    """
    Get all performance rating responses with user information
    Admin only endpoint
    """
    try:
        # Use your existing helper function
        all_performances = getPerformances()
        
        # The getPerformances() already returns dicts with username from the relationship
        return jsonify({
            'responses': all_performances,
            'total': len(all_performances)
        }), 200
        
    except Exception as e:
        print(f"❌ Error in multirating get_responses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to fetch responses',
            'details': str(e)
        }), 500

@multirating_api.route('/my-ratings', methods=['GET'])
@token_required()
def get_my_ratings():
    """
    Get all ratings for the current authenticated user
    """
    try:
        current_user = g.current_user
        
        # Use your existing helper function
        from hacks.performances import getUserPerformances
        user_ratings = getUserPerformances(current_user.id)
        
        # Calculate average
        if user_ratings:
            avg = sum(r['rating'] for r in user_ratings) / len(user_ratings)
        else:
            avg = 0
        
        return jsonify({
            'ratings': user_ratings,
            'total': len(user_ratings),
            'average': round(avg, 1)
        }), 200
        
    except Exception as e:
        print(f"❌ Error in multirating get_my_ratings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to fetch your ratings',
            'details': str(e)
        }), 500