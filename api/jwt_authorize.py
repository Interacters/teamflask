from flask import request
from flask import current_app, g
from functools import wraps
import jwt
from model.user import User

def token_required(roles=None):
    '''
    This function is used to guard API endpoints that require authentication.
    Here is how it works:
      1. checks for the presence of a valid JWT token in the request cookie
      2. decodes the token and retrieves the user data
      3. checks if the user data is found in the database
      4. checks if the user has the required role
      5. set the current_user in the global context (Flask's g object)
      6. returns the decorated function if all checks pass
    Here are some possible error responses:    
      A. 401 / Unauthorized: token is missing or invalid
      B. 403 / Forbidden: user has insufficient permissions
      C. 500 / Internal Server Error: something went wrong with the token decoding
    '''
    def decorator(func_to_guard):
        @wraps(func_to_guard)
        def decorated(*args, **kwargs):
            # DEBUG: Print all cookies
            print(f"🔍 All cookies received: {dict(request.cookies)}")
            print(f"🔍 Looking for cookie: {current_app.config['JWT_TOKEN_NAME']}")
            
            token = request.cookies.get(current_app.config["JWT_TOKEN_NAME"])
            
            if not token:
                print(f"❌ Token NOT found in cookies!")
                print(f"❌ Available cookies: {list(request.cookies.keys())}")
                print(f"❌ Request origin: {request.headers.get('Origin')}")
                print(f"❌ Request host: {request.host}")
                return {
                    "message": "Authentication Token is missing!",
                    "data": None,
                    "error": "Unauthorized"
                }, 401
            
            print(f"✅ Token found: {token[:20]}...")
            
            try:
                # Decode the token and retrieve the user data
                data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                current_user = User.query.filter_by(_uid=data["_uid"]).first()
                if current_user is None:
                    return {
                        "message": "Invalid Authentication token!",
                        "data": None,
                        "error": "Unauthorized"
                    }, 401
                
                # Check user has the required role, when role is required 
                if roles and current_user.role not in roles:
                    return {
                        "message": "Insufficient permissions. Required roles: {}".format(roles),
                        "data": None,
                        "error": "Forbidden"
                    }, 403
                
                # Success finding user and (optional) role
                g.current_user = current_user
                print(f"✅ User authenticated: {current_user.uid}")
            
            except Exception as e:
                print(f"❌ Token decode error: {e}")
                return {
                    "message": "Something went wrong decoding the token!",
                    "data": None,
                    "error": str(e)
                }, 500

            # If this is a CORS preflight request, return 200 OK immediately
            if request.method == 'OPTIONS':
                return ('', 200)

            return func_to_guard(*args, **kwargs)

        return decorated

    return decorator
