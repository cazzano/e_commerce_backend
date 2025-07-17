from flask import Blueprint, request, jsonify
import sqlite3
from modules.e_commerce.authentication_decorator import token_required

# Create blueprint
get_products_bp = Blueprint('get_products', __name__)

# Get all products endpoint
@get_products_bp.route('/products', methods=['GET'])
@token_required
def get_all_products():
    """Get all products from the database with optional filtering"""
    try:
        conn = sqlite3.connect('products.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get query parameters for filtering
        category_type = request.args.get('category_type')
        category_name = request.args.get('category_name')
        brand = request.args.get('brand')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        in_stock_only = request.args.get('in_stock_only', 'false').lower() == 'true'
        
        # Build query with filters
        query = 'SELECT * FROM products WHERE 1=1'
        params = []
        
        if category_type:
            query += ' AND category_type = ?'
            params.append(category_type)
        
        if category_name:
            query += ' AND category_name = ?'
            params.append(category_name)
        
        if brand:
            query += ' AND brand = ?'
            params.append(brand)
        
        if min_price:
            query += ' AND price >= ?'
            params.append(float(min_price))
        
        if max_price:
            query += ' AND price <= ?'
            params.append(float(max_price))
        
        if in_stock_only:
            query += ' AND stock > 0'
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        
        conn.close()
        
        # Convert to list of dictionaries
        products_list = []
        for product in products:
            products_list.append({
                'product_id': product['product_id'],
                'name': product['name'],
                'price': product['price'],
                'stock': product['stock'],
                'incoming': product['incoming'],
                'category_type': product['category_type'],
                'category_name': product['category_name'],
                'sub_category': product['sub_category'],
                'brand': product['brand'],
                'description': product['description'],
                'specifications': product['specifications'],
                'delivery_charges': product['delivery_charges'],
                'delivery_day': product['delivery_day'],
                'discounts': product['discounts'],
                'created_at': product['created_at']
            })
        
        return jsonify({
            'products': products_list,
            'total_count': len(products_list),
            'filters_applied': {
                'category_type': category_type,
                'category_name': category_name,
                'brand': brand,
                'min_price': min_price,
                'max_price': max_price,
                'in_stock_only': in_stock_only
            },
            'status': 'success'
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

# Get single product by ID
@get_products_bp.route('/products/<int:product_id>', methods=['GET'])
@token_required
def get_product_by_id(product_id):
    """Get a specific product by its ID"""
    try:
        conn = sqlite3.connect('products.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
        product = cursor.fetchone()
        
        conn.close()
        
        if not product:
            return jsonify({
                'error': 'Product not found',
                'status': 'not_found'
            }), 404
        
        product_data = {
            'product_id': product['product_id'],
            'name': product['name'],
            'price': product['price'],
            'stock': product['stock'],
            'incoming': product['incoming'],
            'category_type': product['category_type'],
            'category_name': product['category_name'],
            'sub_category': product['sub_category'],
            'brand': product['brand'],
            'description': product['description'],
            'specifications': product['specifications'],
            'delivery_charges': product['delivery_charges'],
            'delivery_day': product['delivery_day'],
            'discounts': product['discounts'],
            'created_at': product['created_at']
        }
        
        return jsonify({
            'product': product_data,
            'status': 'success'
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


