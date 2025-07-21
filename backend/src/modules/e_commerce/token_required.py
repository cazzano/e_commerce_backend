from functools import wraps
from flask import jsonify, request
import jwt

# Configuration - Should match your JWT_SECRET_KEY from login_jwt.py
JWT_SECRET_KEY = 'djfghjkoUK)#$&*^#$&dhfgdjh*@&##&*$dhfgdO&*@#)&@#_dpFJKDGPRUK384#)*&$%^#dkjf3784512SDF'

def token_required(f):
    """Decorator to validate JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Authorization token is required!'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode the token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = {
                'user_id': payload['user_id'],
                'username': payload['username']
            }
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


