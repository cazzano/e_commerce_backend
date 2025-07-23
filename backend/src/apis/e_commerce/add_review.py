from flask import jsonify, Blueprint, request
import jwt
import sqlite3
import os
from functools import wraps

# Configuration - Should match your existing JWT secret
JWT_SECRET_KEY = 'djfghjkoUK)#$&*^#$&dhfgdjh*@&##&*$dhfgdO&*@#)&@#_dpFJKDGPRUK384#)*&$%^#dkjf3784512SDF'

review_api = Blueprint('review_api', __name__)

def init_review_database():
    """Initialize the review database and create table if not exists"""
    try:
        conn = sqlite3.connect('review.db')
        cursor = conn.cursor()
        
        # Create reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                review TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Review database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing review database: {e}")

def token_required(f):
    """Decorator to verify JWT token and extract user information"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Extract token from "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format. Use: Bearer <token>'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            current_username = data['username']
            
            # Pass user info to the route function
            return f(current_user_id, current_username, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        except KeyError as e:
            return jsonify({'error': f'Token missing required field: {str(e)}'}), 401
            
    return decorated

@review_api.route('/reviews', methods=['POST'])
@token_required
def add_review(user_id, username):
    """Add a new review with automatic user info extraction from JWT"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required!'}), 400
        
        # Validate required fields
        if not data.get('review') or not data.get('rating'):
            return jsonify({'error': 'Review and rating are required!'}), 400
        
        review_text = data['review'].strip()
        rating = data['rating']
        
        # Validate review text
        if not review_text:
            return jsonify({'error': 'Review cannot be empty!'}), 400
        
        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5!'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Rating must be a valid integer!'}), 400
        
        # Insert review into database
        conn = sqlite3.connect('review.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reviews (user_id, username, review, rating)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, review_text, rating))
        
        review_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Review added successfully!',
            'review_id': review_id,
            'user_id': user_id,
            'username': username,
            'review': review_text,
            'rating': rating
        }), 201
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Error adding review: {e}")
        return jsonify({'error': 'An error occurred while adding the review'}), 500

@review_api.route('/reviews', methods=['GET'])
def get_all_reviews():
    """Get all reviews (no authentication required for viewing)"""
    try:
        conn = sqlite3.connect('review.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT review_id, user_id, username, review, rating, created_at
            FROM reviews
            ORDER BY created_at DESC
        ''')
        
        reviews = cursor.fetchall()
        conn.close()
        
        # Format the response
        review_list = []
        for review in reviews:
            review_list.append({
                'review_id': review[0],
                'user_id': review[1],
                'username': review[2],
                'review': review[3],
                'rating': review[4],
                'created_at': review[5]
            })
        
        return jsonify({
            'reviews': review_list,
            'total_count': len(review_list)
        }), 200
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return jsonify({'error': 'An error occurred while fetching reviews'}), 500

@review_api.route('/reviews/user', methods=['GET'])
@token_required
def get_user_reviews(user_id, username):
    """Get reviews by the current authenticated user"""
    try:
        conn = sqlite3.connect('review.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT review_id, user_id, username, review, rating, created_at
            FROM reviews
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        reviews = cursor.fetchall()
        conn.close()
        
        # Format the response
        review_list = []
        for review in reviews:
            review_list.append({
                'review_id': review[0],
                'user_id': review[1],
                'username': review[2],
                'review': review[3],
                'rating': review[4],
                'created_at': review[5]
            })
        
        return jsonify({
            'reviews': review_list,
            'total_count': len(review_list),
            'user_info': {
                'user_id': user_id,
                'username': username
            }
        }), 200
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Error fetching user reviews: {e}")
        return jsonify({'error': 'An error occurred while fetching reviews'}), 500

@review_api.route('/reviews/<int:review_id>', methods=['DELETE'])
@token_required
def delete_review(user_id, username, review_id):
    """Delete a review (only by the user who created it)"""
    try:
        conn = sqlite3.connect('review.db')
        cursor = conn.cursor()
        
        # Check if review exists and belongs to the user
        cursor.execute('''
            SELECT user_id FROM reviews WHERE review_id = ?
        ''', (review_id,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'Review not found!'}), 404
        
        if result[0] != user_id:
            conn.close()
            return jsonify({'error': 'You can only delete your own reviews!'}), 403
        
        # Delete the review
        cursor.execute('''
            DELETE FROM reviews WHERE review_id = ? AND user_id = ?
        ''', (review_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Review deleted successfully!',
            'review_id': review_id
        }), 200
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Error deleting review: {e}")
        return jsonify({'error': 'An error occurred while deleting the review'}), 500

# Initialize the database when the module is imported
init_review_database()
