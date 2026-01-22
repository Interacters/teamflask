from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from model.user import User

# Create Blueprint
promote_admin_api = Blueprint('promote_admin_api', __name__, url_prefix='/api')
api = Api(promote_admin_api)


class PromoteToAdmin(Resource):
    def post(self):
        """
        Promote a user to Admin role.
        """
        body = request.get_json()
        
        if not body:
            return {'message': 'Request body is required'}, 400
        
        # Get target user ID
        uid = body.get('uid')
        if not uid:
            return {'message': 'UID is required'}, 400
        
        # Find user in database
        user = User.query.filter_by(_uid=uid).first()
        
        if not user:
            # List available users to help debug
            all_users = User.query.all()
            available_uids = [u.uid for u in all_users]
            return {
                'message': f'User "{uid}" not found',
                'available_users': available_uids
            }, 404
        
        # Check current role
        if user.role == 'Admin':
            return {
                'message': f'User {uid} is already an Admin',
                'user': {
                    'uid': user.uid,
                    'name': user.name,
                    'role': user.role
                }
            }, 200
        
        # Promote to Admin
        user.update({'role': 'Admin'})
        
        return {
            'message': f'🎉 SUCCESS! {user.name} is now an Admin!',
            'user': {
                'uid': user.uid,
                'name': user.name,
                'email': user.email,
                'role': user.role
            },
            'warning': '⚠️ REMEMBER TO DELETE api/promote_admin.py AFTER USE!'
        }, 200
    
    def get(self):
        """
        Check if this endpoint is active (for testing).
        """
        return {
            'status': 'active',
            'message': 'Admin promotion endpoint is running',
            'endpoint': '/api/promote-admin',
            'warning': '⚠️ This is a security risk - delete this file after creating your admin!'
        }, 200


# Register the resource
api.add_resource(PromoteToAdmin, '/promote-admin')