from flask import request, jsonify
from functools import wraps
import jwt

# Secret token for authentication (should be moved to environment variables in production)
SECRET_TOKEN = "DMFGHO#$&*I)@#IUDSJIFGUI)SDR)*&#$&#@$^SDFGY@()!&@*DJSGF)#$&*#^"

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing', 'status': 'unauthorized'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode JWT token using the secret
            payload = jwt.decode(token, SECRET_TOKEN, algorithms=['HS256'])
            
            # You can access payload data here if needed
            # For example: user_id = payload.get('user_id')
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired', 'status': 'unauthorized'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid', 'status': 'unauthorized'}), 401
        except Exception as e:
            return jsonify({'error': 'Token validation failed', 'status': 'unauthorized'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


