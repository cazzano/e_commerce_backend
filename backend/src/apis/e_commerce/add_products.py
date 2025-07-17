from flask import Blueprint, request, jsonify
import sqlite3
import os
import jwt
from modules.e_commerce.authentication_decorator import token_required
from modules.e_commerce.validation import validate_product_data
from modules.e_commerce.init_db import init_db

# Secret token for authentication (matching your existing system)
SECRET_TOKEN = "DMFGHO#$&*I)@#IUDSJIFGUI)SDR)*&#$&#@$^SDFGY@()!&@*DJSGF)#$&*#^"

# Create blueprint
add_products_bp = Blueprint('add_products', __name__)


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


@add_products_bp.route('/add/products/form', methods=['POST'])
@token_required
def add_product_form():
    """Add a new product using form data for a specific seller"""
    try:
        # Get user ID from token (matching your existing auth system)
        token = request.headers.get('Authorization')
        try:
            user_id = get_user_id_from_token(token)
        except ValueError as e:
            return jsonify({
                'error': str(e),
                'status': 'token_error'
            }), 401
        
        # Get form data
        data = {}
        
        # Required fields
        required_fields = ['name', 'price', 'stock', 'category_type', 'category_name']
        for field in required_fields:
            value = request.form.get(field)
            if value is not None:
                data[field] = value.strip()
        
        # Optional fields
        optional_fields = ['incoming', 'sub_category', 'brand', 'description', 
                          'specifications', 'delivery_charges', 'delivery_day', 'discounts']
        for field in optional_fields:
            value = request.form.get(field)
            if value is not None and value.strip():
                data[field] = value.strip()
        
        # Convert numeric fields
        numeric_conversions = {
            'price': float,
            'stock': int,
            'incoming': int,
            'delivery_charges': float,
            'delivery_day': int,
            'discounts': float
        }
        
        for field, converter in numeric_conversions.items():
            if field in data and data[field]:
                try:
                    data[field] = converter(data[field])
                except ValueError:
                    return jsonify({
                        'error': f'Invalid numeric value for {field}: {data[field]}',
                        'status': 'validation_error'
                    }), 400
        
        # Validate the data
        is_valid, message = validate_product_data(data)
        if not is_valid:
            return jsonify({
                'error': message,
                'status': 'validation_error',
                'received_data': data
            }), 400
        
        # Initialize database if it doesn't exist
        if not os.path.exists('products.db'):
            init_db()
        
        # Connect to database
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # CHECK FOR DUPLICATE PRODUCT NAME FOR THIS SPECIFIC USER/SELLER
        cursor.execute('''
            SELECT product_id, name FROM products 
            WHERE LOWER(name) = LOWER(?) AND user_id = ?
        ''', (data['name'], user_id))
        existing_product = cursor.fetchone()
        
        if existing_product:
            conn.close()
            return jsonify({
                'error': f'You already have a product with name "{data["name"]}"',
                'status': 'duplicate_product',
                'existing_product': {
                    'product_id': existing_product[0],
                    'name': existing_product[1]
                },
                'message': 'Product name must be unique within your store. Please choose a different name or update your existing product.'
            }), 409  # 409 Conflict status code
        
        # Insert product data with user_id
        cursor.execute('''
            INSERT INTO products (
                user_id, name, price, stock, incoming, category_type, category_name,
                sub_category, brand, description, specifications,
                delivery_charges, delivery_day, discounts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data['name'],
            data['price'],
            data['stock'],
            data.get('incoming', 0),
            data['category_type'],
            data['category_name'],
            data.get('sub_category'),
            data.get('brand'),
            data.get('description'),
            data.get('specifications'),
            data.get('delivery_charges', 0.0),
            data.get('delivery_day', 1),
            data.get('discounts', 0.0)
        ))
        
        # Get the inserted product ID
        product_id = cursor.lastrowid
        
        # Commit and close connection
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product added successfully',
            'status': 'success',
            'product_id': product_id,
            'user_id': user_id,
            'data': {
                'product_id': product_id,
                'user_id': user_id,
                'name': data['name'],
                'price': data['price'],
                'stock': data['stock'],
                'category_type': data['category_type'],
                'category_name': data['category_name']
            }
        }), 201
        
    except sqlite3.Error as e:
        return jsonify({
            'error': f'Database error: {str(e)}',
            'status': 'database_error'
        }), 500
    
    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'status': 'internal_error'
        }), 500


@add_products_bp.route('/my/products', methods=['GET'])
@token_required
def get_my_products():
    """Get all products for the authenticated user/seller"""
    try:
        # Get user ID from token
        token = request.headers.get('Authorization')
        try:
            user_id = get_user_id_from_token(token)
        except ValueError as e:
            return jsonify({
                'error': str(e),
                'status': 'token_error'
            }), 401
        
        # Connect to database
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # Get all products for this user/seller
        cursor.execute('''
            SELECT product_id, name, price, stock, incoming, category_type, 
                   category_name, sub_category, brand, description, specifications,
                   delivery_charges, delivery_day, discounts, created_at
            FROM products 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        products = cursor.fetchall()
        conn.close()
        
        # Format the response
        products_list = []
        for product in products:
            products_list.append({
                'product_id': product[0],
                'name': product[1],
                'price': product[2],
                'stock': product[3],
                'incoming': product[4],
                'category_type': product[5],
                'category_name': product[6],
                'sub_category': product[7],
                'brand': product[8],
                'description': product[9],
                'specifications': product[10],
                'delivery_charges': product[11],
                'delivery_day': product[12],
                'discounts': product[13],
                'created_at': product[14]
            })
        
        return jsonify({
            'message': 'Products retrieved successfully',
            'status': 'success',
            'user_id': user_id,
            'total_products': len(products_list),
            'products': products_list
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'error': f'Database error: {str(e)}',
            'status': 'database_error'
        }), 500
    
    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'status': 'internal_error'
        }), 500
