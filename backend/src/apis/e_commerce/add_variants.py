from flask import Blueprint, request, jsonify
import sqlite3
import os
from modules.e_commerce.authentication_decorator import token_required
from modules.e_commerce.init_variants_db import init_variants_db, verify_product_exists
from modules.e_commerce.variant_validation import validate_bulk_variants_data
from modules.e_commerce.get_user_id_from_token import get_user_id_from_token

# Create blueprint
product_variants_bp = Blueprint('product_variants', __name__)


@product_variants_bp.route('/add/product/variants/bulk', methods=['POST'])
@token_required
def add_product_variants_bulk():
    """Add multiple variants to products in bulk"""
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
        
        # Get JSON data
        data = request.get_json()
        if not data or 'variants' not in data:
            return jsonify({
                'error': 'No variants data provided. Expected format: {"variants": [...]}',
                'status': 'validation_error'
            }), 400
        
        variants_list = data['variants']
        
        # Validate bulk data
        is_valid, message = validate_bulk_variants_data(variants_list)
        if not is_valid:
            return jsonify({
                'error': message,
                'status': 'validation_error'
            }), 400
        
        # Verify all products exist and belong to user
        product_ids = list(set([variant['product_id'] for variant in variants_list]))
        for product_id in product_ids:
            product_exists, product_info = verify_product_exists(product_id, user_id)
            if not product_exists:
                return jsonify({
                    'error': f'Product ID {product_id}: {product_info}',
                    'status': 'product_not_found'
                }), 404
        
        # Initialize variants database if it doesn't exist
        if not os.path.exists('variants.db'):
            init_variants_db()
        
        # Connect to variants database
        conn = sqlite3.connect('variants.db')
        cursor = conn.cursor()
        
        # Check for existing variants
        added_variants = []
        skipped_variants = []
        
        for variant in variants_list:
            # Check for duplicate variant name for this product
            cursor.execute('''
                SELECT variant_id, name FROM variants 
                WHERE LOWER(name) = LOWER(?) AND product_id = ? AND user_id = ?
            ''', (variant['name'].strip(), variant['product_id'], user_id))
            existing_variant = cursor.fetchone()
            
            if existing_variant:
                skipped_variants.append({
                    'variant_name': variant['name'],
                    'product_id': variant['product_id'],
                    'reason': 'Variant already exists',
                    'existing_variant_id': existing_variant[0]
                })
                continue
            
            # Insert variant data
            cursor.execute('''
                INSERT INTO variants (
                    product_id, user_id, name, price, description, stock
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                variant['product_id'],
                user_id,
                variant['name'].strip(),
                variant['price'],
                variant.get('description', '').strip() if variant.get('description') else None,
                variant.get('stock', 0)
            ))
            
            # Get the inserted variant ID
            variant_id = cursor.lastrowid
            
            added_variants.append({
                'variant_id': variant_id,
                'product_id': variant['product_id'],
                'name': variant['name'].strip(),
                'price': variant['price'],
                'description': variant.get('description', '').strip() if variant.get('description') else None,
                'stock': variant.get('stock', 0)
            })
        
        # Commit and close connection
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Bulk variant operation completed. Added: {len(added_variants)}, Skipped: {len(skipped_variants)}',
            'status': 'success',
            'user_id': user_id,
            'summary': {
                'total_requested': len(variants_list),
                'added': len(added_variants),
                'skipped': len(skipped_variants)
            },
            'added_variants': added_variants,
            'skipped_variants': skipped_variants
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


@product_variants_bp.route('/product/<int:product_id>/variants', methods=['GET'])
@token_required
def get_product_variants(product_id):
    """Get all variants for a specific product"""
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
        
        # Verify product exists and belongs to user
        product_exists, product_info = verify_product_exists(product_id, user_id)
        if not product_exists:
            return jsonify({
                'error': product_info,
                'status': 'product_not_found'
            }), 404
        
        # Connect to variants database
        conn = sqlite3.connect('variants.db')
        cursor = conn.cursor()
        
        # Get all variants for this product
        cursor.execute('''
            SELECT variant_id, name, price, description, stock, is_active, created_at, updated_at
            FROM variants 
            WHERE product_id = ? AND user_id = ?
            ORDER BY created_at DESC
        ''', (product_id, user_id))
        
        variants = cursor.fetchall()
        conn.close()
        
        # Format the response
        variants_list = []
        for variant in variants:
            variants_list.append({
                'variant_id': variant[0],
                'name': variant[1],
                'price': variant[2],
                'description': variant[3],
                'stock': variant[4],
                'is_active': bool(variant[5]),
                'created_at': variant[6],
                'updated_at': variant[7]
            })
        
        return jsonify({
            'message': 'Product variants retrieved successfully',
            'status': 'success',
            'product_id': product_id,
            'product_name': product_info[1],  # Product name from verify_product_exists
            'user_id': user_id,
            'total_variants': len(variants_list),
            'variants': variants_list
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


@product_variants_bp.route('/my/variants', methods=['GET'])
@token_required
def get_my_variants():
    """Get all variants for all products owned by the authenticated user"""
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
        
        # Connect to variants database
        conn = sqlite3.connect('variants.db')
        cursor = conn.cursor()
        
        # Get all variants for this user with product information
        cursor.execute('''
            SELECT v.variant_id, v.product_id, v.name, v.price, v.description, 
                   v.stock, v.is_active, v.created_at, v.updated_at
            FROM variants v
            WHERE v.user_id = ?
            ORDER BY v.product_id, v.created_at DESC
        ''', (user_id,))
        
        variants = cursor.fetchall()
        conn.close()
        
        # Get product information for grouping
        if variants:
            # Get unique product IDs
            product_ids = list(set([variant[1] for variant in variants]))
            
            # Get product information
            products_conn = sqlite3.connect('products.db')
            products_cursor = products_conn.cursor()
            
            placeholders = ','.join(['?' for _ in product_ids])
            products_cursor.execute(f'''
                SELECT product_id, name FROM products 
                WHERE product_id IN ({placeholders}) AND user_id = ?
            ''', product_ids + [user_id])
            
            products_info = {row[0]: row[1] for row in products_cursor.fetchall()}
            products_conn.close()
        else:
            products_info = {}
        
        # Group variants by product
        products_with_variants = {}
        for variant in variants:
            product_id = variant[1]
            if product_id not in products_with_variants:
                products_with_variants[product_id] = {
                    'product_id': product_id,
                    'product_name': products_info.get(product_id, 'Unknown Product'),
                    'variants': []
                }
            
            products_with_variants[product_id]['variants'].append({
                'variant_id': variant[0],
                'name': variant[2],
                'price': variant[3],
                'description': variant[4],
                'stock': variant[5],
                'is_active': bool(variant[6]),
                'created_at': variant[7],
                'updated_at': variant[8]
            })
        
        return jsonify({
            'message': 'All variants retrieved successfully',
            'status': 'success',
            'user_id': user_id,
            'total_products_with_variants': len(products_with_variants),
            'total_variants': len(variants),
            'products_with_variants': list(products_with_variants.values())
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




