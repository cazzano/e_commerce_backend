from flask import request, jsonify, Blueprint
import sqlite3
from modules.e_commerce.token_required import token_required
from modules.e_commerce.init_products_db import init_products_db
from modules.e_commerce.get_next_product_id import get_next_product_id

# Configuration
PRODUCTS_DATABASE = 'products.db'

products_api = Blueprint('products_api', __name__)

@products_api.route('/auth/add/products', methods=['POST'])
@token_required
def add_product(current_user_id, current_username):
    """Add a new product to the database"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['product_name', 'price', 'discount', 'rating', 'shipping', 'brand', 'selling']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate data types and values
        try:
            price = float(data['price'])
            discount = float(data['discount'])
            rating = float(data['rating'])
            selling = int(data['selling'])
            
            if price < 0:
                return jsonify({'error': 'Price must be non-negative'}), 400
            if discount < 0 or discount > 100:
                return jsonify({'error': 'Discount must be between 0 and 100'}), 400
            if rating < 0 or rating > 5:
                return jsonify({'error': 'Rating must be between 0 and 5'}), 400
            if selling < 0:
                return jsonify({'error': 'Selling count must be non-negative'}), 400
                
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid data types for numeric fields'}), 400
        
        product_name = data['product_name'].strip()
        shipping = data['shipping'].strip()
        brand = data['brand'].strip()
        
        # Validate string fields
        if not product_name or len(product_name) > 255:
            return jsonify({'error': 'Product name must be 1-255 characters'}), 400
        if not brand or len(brand) > 100:
            return jsonify({'error': 'Brand must be 1-100 characters'}), 400
        if not shipping or len(shipping) > 100:
            return jsonify({'error': 'Shipping info must be 1-100 characters'}), 400
        
        # Generate new product ID
        product_id = get_next_product_id()
        
        # Insert into database
        conn = sqlite3.connect(PRODUCTS_DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (
                product_id, product_name, price, discount, rating, 
                shipping, brand, selling, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id, product_name, price, discount, rating,
            shipping, brand, selling, current_user_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product added successfully!',
            'product_id': product_id,
            'product_name': product_name,
            'price': price,
            'discount': discount,
            'rating': rating,
            'shipping': shipping,
            'brand': brand,
            'selling': selling,
            'created_by': current_user_id,
            'created_by_username': current_username
        }), 201
        
    except sqlite3.IntegrityError as e:
        return jsonify({'error': 'Database constraint error'}), 400
    except Exception as e:
        print(f"Add product error: {e}")
        return jsonify({'error': 'An error occurred while adding the product'}), 500

@products_api.route('/products/<product_id>', methods=['GET'])
@token_required
def get_product(current_user_id, current_username, product_id):
    """Get a specific product by ID (bonus endpoint)"""
    try:
        conn = sqlite3.connect(PRODUCTS_DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT product_id, product_name, price, discount, rating,
                   shipping, brand, selling, created_at, updated_at
            FROM products WHERE product_id = ?
        ''', (product_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Product not found'}), 404
        
        product = {
            'product_id': result[0],
            'product_name': result[1],
            'price': result[2],
            'discount': result[3],
            'rating': result[4],
            'shipping': result[5],
            'brand': result[6],
            'selling': result[7],
            'created_at': result[8],
            'updated_at': result[9]
        }
        
        return jsonify(product), 200
        
    except Exception as e:
        print(f"Get product error: {e}")
        return jsonify({'error': 'An error occurred while fetching the product'}), 500

# Initialize database when module is imported
init_products_db()

