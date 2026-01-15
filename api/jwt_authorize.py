from flask import request, current_app, g
from functools import wraps
import jwt
from model.user import User

def token_required(roles=None):
    '''
    Guard API endpoints with JWT token validation.
    
    Checks:
    1. JWT token presence in cookies
    2. Token validity and expiration
    3. User exists in database
    4. User has required role (if specified)
    
    Sets g.current_user for use in decorated function.
    '''
    def decorator(func_to_guard):
        @wraps(func_to_guard)
        def decorated(*args, **kwargs):
            # ===== STEP 1: Get token from cookie =====
            # Try standard JWT token name first
            token = request.cookies.get(current_app.config.get("JWT_TOKEN_NAME"))
            
            # If not found, try alternative name (for compatibility)
            if not token:
                token = request.cookies.get("jwt_python_flask")
            
            # If still not found, check Authorization header as fallback
            if not token:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split('Bearer ')[1]
            
            # ===== STEP 2: Token validation =====
            if not token:
                return {
                    "message": "Authentication Token is missing!",
                    "data": None,
                    "error": "Unauthorized"
                }, 401
            
            try:
                # Decode JWT token
                data = jwt.decode(
                    token, 
                    current_app.config["SECRET_KEY"], 
                    algorithms=["HS256"]
                )
                
                # ===== STEP 3: Validate user exists =====
                current_user = User.query.filter_by(_uid=data.get("_uid")).first()
                if current_user is None:
                    return {
                        "message": "Invalid Authentication token! User not found.",
                        "data": None,
                        "error": "Unauthorized"
                    }, 401
                
                # ===== STEP 4: Check role requirement (if specified) =====
                if roles and current_user.role not in roles:
                    return {
                        "message": f"Insufficient permissions. Required roles: {roles}",
                        "data": None,
                        "error": "Forbidden"
                    }, 403
                
                # ===== STEP 5: Set global user context =====
                g.current_user = current_user
                
                # Handle CORS preflight
                if request.method == 'OPTIONS':
                    return ('', 200)
                
                # Success: call decorated function
                return func_to_guard(*args, **kwargs)
            
            except jwt.ExpiredSignatureError:
                return {
                    "message": "Token has expired!",
                    "data": None,
                    "error": "Unauthorized"
                }, 401
            
            except jwt.InvalidTokenError as e:
                return {
                    "message": "Invalid token!",
                    "data": None,
                    "error": str(e)
                }, 401
            
            except Exception as e:
                return {
                    "message": "Error decoding token!",
                    "data": None,
                    "error": str(e)
                }, 500
        
        return decorated
    
    return decorator


# ===== UTILITY FUNCTION FOR OPTIONAL AUTH =====
def get_current_user():
    """
    Try to get current user without raising errors.
    Returns None if not authenticated.
    """
    try:
        return g.current_user if hasattr(g, 'current_user') else None
    except:
        return None