
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from model.performance import MultiRating

performance_api = Blueprint('performance_api', __name__, url_prefix='/api')


@performances_api.route('/multirating/responses', methods=['GET'])
@login_required
def get_all_multirating_responses():
    """
    Get all rating responses (admin only)
    
    Returns list of all submissions with all questions
    """
    try:
        # Check admin permission
        if current_user.role != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        responses = MultiRating.get_all()
        return jsonify(responses), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

