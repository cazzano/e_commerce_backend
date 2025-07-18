import jwt

SECRET_TOKEN = "DMFGHO#$&*I)@#IUDSJIFGUI)SDR)*&#$&#@$^SDFGY@()!&@*DJSGF)#$&*#^"

def get_user_id_from_token(token):
    """Extract user_id from JWT token (matching your existing auth system)"""
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode JWT token
        payload = jwt.decode(token, SECRET_TOKEN, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        if not user_id:
            raise ValueError("user_id not found in token")
            
        return user_id
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")


