from flask import request, jsonify,Blueprint
import sqlite3
from werkzeug.security import generate_password_hash
from modules.registration.buyer.automatically_make_user_id import get_next_user_id


# Database configuration
DATABASE = 'buyers.db'


signup_login_buyer=Blueprint('signup_login_buyer',__name__)


@signup_login_buyer.route('/register/buyer', methods=['POST'])
def register_user():
    """Register a new user with username and password from headers"""
    try:
        # Get username and password from headers
        username = request.headers.get('username')
        password = request.headers.get('password')

        # Validate required headers
        if not username or not password:
            return jsonify({
                'error': 'Missing required headers: username and password'
            }), 400

        # Check if username already exists
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'error': 'Username already exists'
            }), 409

        # Generate user ID and hash password
        user_id = get_next_user_id()
        password_hash = generate_password_hash(password)

        # Insert new user
        cursor.execute('''
            INSERT INTO users (user_id, username, password_hash)
            VALUES (?, ?, ?)
        ''', (user_id, username, password_hash))

        conn.commit()
        conn.close()

        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'username': username
        }), 201

    except Exception as e:
        return jsonify({
            'error': f'Registration failed: {str(e)}'
        }), 500
