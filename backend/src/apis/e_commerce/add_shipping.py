from flask import jsonify, Blueprint, request
import jwt
import sqlite3
from functools import wraps

# Configuration - Should match your existing JWT secret
JWT_SECRET_KEY = 'djfghjkoUK)#$&*^#$&dhfgdjh*@&##&*$dhfgdO&*@#)&@#_dpFJKDGPRUK384#)*&$%^#dkjf3784512SDF'

shipping_api = Blueprint('shipping_api', __name__)

def token_required(f):
    """Decorator to require JWT token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
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

def init_shipping_database():
    """Initialize the shipping database and create table if it doesn't exist"""
    try:
        conn = sqlite3.connect('shipping.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shipping_info (
                shipping_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                region TEXT NOT NULL,
                number TEXT NOT NULL,
                street_address TEXT NOT NULL,
                land_mark TEXT,
                province TEXT NOT NULL,
                city TEXT NOT NULL,
                zip_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Shipping database initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing shipping database: {e}")
        return False

@shipping_api.route('/shipping/add', methods=['POST'])
@token_required
def add_shipping_info(current_user):
    """Add shipping information for authenticated user"""
    try:
        # Initialize database if not exists
        if not init_shipping_database():
            return jsonify({'error': 'Database initialization failed'}), 500
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['region', 'number', 'street_address', 'province', 'city', 'zip_code']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Extract shipping information
        region = data['region']
        number = data['number']
        street_address = data['street_address']
        land_mark = data.get('land_mark', '')  # Optional field
        province = data['province']
        city = data['city']
        zip_code = data['zip_code']
        
        # Get user info from decoded token
        user_id = current_user['user_id']
        username = current_user['username']
        
        # Insert into shipping database
        conn = sqlite3.connect('shipping.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shipping_info 
            (user_id, username, region, number, street_address, land_mark, province, city, zip_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, region, number, street_address, land_mark, province, city, zip_code))
        
        shipping_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Shipping information added successfully!',
            'shipping_id': shipping_id,
            'user_id': user_id,
            'username': username,
            'shipping_details': {
                'region': region,
                'number': number,
                'street_address': street_address,
                'land_mark': land_mark,
                'province': province,
                'city': city,
                'zip_code': zip_code
            }
        }), 201
        
    except Exception as e:
        print(f"Error adding shipping info: {e}")
        return jsonify({'error': 'An error occurred while adding shipping information'}), 500

@shipping_api.route('/shipping/user', methods=['GET'])
@token_required
def get_user_shipping_info(current_user):
    """Get all shipping information for the authenticated user"""
    try:
        user_id = current_user['user_id']
        
        conn = sqlite3.connect('shipping.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT shipping_id, region, number, street_address, land_mark, 
                   province, city, zip_code, created_at
            FROM shipping_info 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        shipping_list = []
        for row in results:
            shipping_list.append({
                'shipping_id': row[0],
                'region': row[1],
                'number': row[2],
                'street_address': row[3],
                'land_mark': row[4],
                'province': row[5],
                'city': row[6],
                'zip_code': row[7],
                'created_at': row[8]
            })
        
        return jsonify({
            'message': 'Shipping information retrieved successfully!',
            'user_id': user_id,
            'username': current_user['username'],
            'shipping_addresses': shipping_list,
            'total_addresses': len(shipping_list)
        }), 200
        
    except Exception as e:
        print(f"Error retrieving shipping info: {e}")
        return jsonify({'error': 'An error occurred while retrieving shipping information'}), 500

@shipping_api.route('/shipping/<int:shipping_id>', methods=['DELETE'])
@token_required
def delete_shipping_info(current_user, shipping_id):
    """Delete a specific shipping address for the authenticated user"""
    try:
        user_id = current_user['user_id']
        
        conn = sqlite3.connect('shipping.db')
        cursor = conn.cursor()
        
        # Check if the shipping address belongs to the user
        cursor.execute('SELECT user_id FROM shipping_info WHERE shipping_id = ?', (shipping_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'Shipping address not found'}), 404
        
        if result[0] != user_id:
            conn.close()
            return jsonify({'error': 'Unauthorized to delete this shipping address'}), 403
        
        # Delete the shipping address
        cursor.execute('DELETE FROM shipping_info WHERE shipping_id = ?', (shipping_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Shipping address deleted successfully!',
            'shipping_id': shipping_id
        }), 200
        
    except Exception as e:
        print(f"Error deleting shipping info: {e}")
        return jsonify({'error': 'An error occurred while deleting shipping information'}), 500
