from flask import jsonify, Blueprint, request
import jwt
import sqlite3
import os
from datetime import datetime
from functools import wraps

# Configuration - Should match the JWT secret from login_jwt.py
JWT_SECRET_KEY = 'djfghjkoUK)#$&*^#$&dhfgdjh*@&##&*$dhfgdO&*@#)&@#_dpFJKDGPRUK384#)*&$%^#dkjf3784512SDF'

profile_api = Blueprint('profile_api', __name__)

def token_required(f):
    """Decorator to verify JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            current_username = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user_id, current_username, *args, **kwargs)
    return decorated

def init_profile_db():
    """Initialize the profile database and create table if it doesn't exist"""
    try:
        conn = sqlite3.connect('profile.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                gender TEXT,
                email_address TEXT,
                birthday TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Profile database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing profile database: {e}")

@profile_api.route('/profile', methods=['POST'])
@token_required
def create_or_update_profile(current_user_id, current_username):
    """Create or update user profile information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields (at least one should be provided)
        allowed_fields = ['gender', 'email_address', 'birthday']
        provided_fields = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
        
        if not provided_fields:
            return jsonify({'error': 'At least one profile field (gender, email_address, birthday) must be provided'}), 400
        
        # Validate email format if provided
        if 'email_address' in provided_fields:
            email = provided_fields['email_address']
            if '@' not in email or '.' not in email.split('@')[-1]:
                return jsonify({'error': 'Invalid email address format'}), 400
        
        # Validate birthday format if provided (expecting YYYY-MM-DD)
        if 'birthday' in provided_fields:
            birthday = provided_fields['birthday']
            try:
                datetime.strptime(birthday, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid birthday format. Use YYYY-MM-DD'}), 400
        
        # Initialize database
        init_profile_db()
        
        conn = sqlite3.connect('profile.db')
        cursor = conn.cursor()
        
        # Check if profile already exists
        cursor.execute("SELECT profile_id FROM profile WHERE user_id = ?", (current_user_id,))
        existing_profile = cursor.fetchone()
        
        if existing_profile:
            # Update existing profile
            update_fields = []
            update_values = []
            
            for field, value in provided_fields.items():
                update_fields.append(f"{field} = ?")
                update_values.append(value)
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(current_user_id)
            
            update_query = f"UPDATE profile SET {', '.join(update_fields)} WHERE user_id = ?"
            cursor.execute(update_query, update_values)
            
            message = 'Profile updated successfully!'
            
        else:
            # Create new profile
            fields = ['user_id', 'username'] + list(provided_fields.keys())
            values = [current_user_id, current_username] + list(provided_fields.values())
            placeholders = ', '.join(['?' for _ in fields])
            
            insert_query = f"INSERT INTO profile ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(insert_query, values)
            
            message = 'Profile created successfully!'
        
        conn.commit()
        
        # Get the updated/created profile
        cursor.execute("""
            SELECT profile_id, user_id, username, gender, email_address, birthday, 
                   created_at, updated_at 
            FROM profile WHERE user_id = ?
        """, (current_user_id,))
        
        profile_data = cursor.fetchone()
        conn.close()
        
        if profile_data:
            profile_info = {
                'profile_id': profile_data[0],
                'user_id': profile_data[1],
                'username': profile_data[2],
                'gender': profile_data[3],
                'email_address': profile_data[4],
                'birthday': profile_data[5],
                'created_at': profile_data[6],
                'updated_at': profile_data[7]
            }
            
            return jsonify({
                'message': message,
                'profile': profile_info
            }), 200
        else:
            return jsonify({'error': 'Failed to retrieve profile data'}), 500
            
    except Exception as e:
        print(f"Profile creation/update error: {e}")
        return jsonify({'error': 'An error occurred while processing profile'}), 500

@profile_api.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user_id, current_username):
    """Get user profile information"""
    try:
        init_profile_db()
        
        conn = sqlite3.connect('profile.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT profile_id, user_id, username, gender, email_address, birthday, 
                   created_at, updated_at 
            FROM profile WHERE user_id = ?
        """, (current_user_id,))
        
        profile_data = cursor.fetchone()
        conn.close()
        
        if profile_data:
            profile_info = {
                'profile_id': profile_data[0],
                'user_id': profile_data[1],
                'username': profile_data[2],
                'gender': profile_data[3],
                'email_address': profile_data[4],
                'birthday': profile_data[5],
                'created_at': profile_data[6],
                'updated_at': profile_data[7]
            }
            
            return jsonify({
                'message': 'Profile retrieved successfully!',
                'profile': profile_info
            }), 200
        else:
            return jsonify({'error': 'Profile not found'}), 404
            
    except Exception as e:
        print(f"Profile retrieval error: {e}")
        return jsonify({'error': 'An error occurred while retrieving profile'}), 500

@profile_api.route('/profile', methods=['DELETE'])
@token_required
def delete_profile(current_user_id, current_username):
    """Delete user profile"""
    try:
        init_profile_db()
        
        conn = sqlite3.connect('profile.db')
        cursor = conn.cursor()
        
        # Check if profile exists
        cursor.execute("SELECT profile_id FROM profile WHERE user_id = ?", (current_user_id,))
        existing_profile = cursor.fetchone()
        
        if not existing_profile:
            conn.close()
            return jsonify({'error': 'Profile not found'}), 404
        
        # Delete profile
        cursor.execute("DELETE FROM profile WHERE user_id = ?", (current_user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Profile deleted successfully!'}), 200
        
    except Exception as e:
        print(f"Profile deletion error: {e}")
        return jsonify({'error': 'An error occurred while deleting profile'}), 500
