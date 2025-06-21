from flask import Flask
from functools import wraps
import os

def token_required(f):
    """Decorator to require JWT token for protected routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format. Use: Bearer <token>'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            current_username = data.get('username', 'unknown')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid!'}), 401
        
        return f(current_user_id, current_username, *args, **kwargs)
    
    return decorated
