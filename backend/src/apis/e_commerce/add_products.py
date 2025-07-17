from flask import Blueprint, request, jsonify
import sqlite3
import os
from modules.e_commerce.authentication_decorator import token_required
from modules.e_commerce.validation import validate_product_data
from modules.e_commerce.init_db import init_db

# Create blueprint
add_products_bp = Blueprint('add_products', __name__)


# FIXED: Changed route to match what you're calling in Bruno
@add_products_bp.route('/add/products/form', methods=['POST'])
@token_required
def add_product_form():
    """Add a new product using form data"""
    try:
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
        
        # CHECK FOR DUPLICATE PRODUCT NAME
        cursor.execute('SELECT product_id, name FROM products WHERE LOWER(name) = LOWER(?)', (data['name'],))
        existing_product = cursor.fetchone()
        
        if existing_product:
            conn.close()
            return jsonify({
                'error': f'Product with name "{data["name"]}" already exists',
                'status': 'duplicate_product',
                'existing_product': {
                    'product_id': existing_product[0],
                    'name': existing_product[1]
                },
                'message': 'Product name must be unique. Please choose a different name or update the existing product.'
            }), 409  # 409 Conflict status code
        
        # Insert product data if no duplicate found
        cursor.execute('''
            INSERT INTO products (
                name, price, stock, incoming, category_type, category_name,
                sub_category, brand, description, specifications,
                delivery_charges, delivery_day, discounts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
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
            'data': {
                'product_id': product_id,
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


# Error handlers
@add_products_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found', 'status': 'not_found'}), 404

@add_products_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed', 'status': 'method_not_allowed'}), 405

@add_products_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'status': 'internal_error'}), 500
