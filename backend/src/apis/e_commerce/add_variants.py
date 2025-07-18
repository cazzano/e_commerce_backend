from flask import Blueprint, request, jsonify
import sqlite3
import os
import jwt
from modules.e_commerce.authentication_decorator import token_required
from modules.e_commerce.init_variants_db import init_variants_db, verify_product_exists
from modules.e_commerce.variant_validation import validate_variant_data, validate_bulk_variants_data

# Secret token for authentication (matching your existing system)
SECRET_TOKEN = "DMFGHO#$&*I)@#IUDSJIFGUI)SDR)*&#$&#@$^SDFGY@()!&@*DJSGF)#$&*#^"

# Create blueprint
product_variants_bp = Blueprint('product_variants', __name__)


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


@product_variants_bp.route('/add/product/variant', methods=['POST'])
@token_required
def add_product_variant():
    """Add a single variant to a product"""
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
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'validation_error'
            }), 400
        
        # Validate the data
        is_valid, message = validate_variant_data(data)
        if not is_valid:
            return jsonify({
                'error': message,
                'status': 'validation_error',
                'received_data': data
            }), 400
        
        # Verify product exists and belongs to user
        product_exists, product_info = verify_product_exists(data['product_id'], user_id)
        if not product_exists:
            return jsonify({
                'error': product_info,
                'status': 'product_not_found'
            }), 404
        
        # Initialize variants database if it doesn't exist
        if not os.path.exists('variants.db'):
            init_variants_db()
        
        # Connect to variants database
        conn = sqlite3.connect('variants.db')
        cursor = conn.cursor()
        
        # Check for duplicate variant name for this product
        cursor.execute('''
            SELECT variant_id, name FROM variants 
            WHERE LOWER(name) = LOWER(?) AND product_id = ? AND user_id = ?
        ''', (data['name'].strip(), data['product_id'], user_id))
        existing_variant = cursor.fetchone()
        
        if existing_variant:
            conn.close()
            return jsonify({
                'error': f'Variant with name "{data["name"]}" already exists for this product',
                'status': 'duplicate_variant',
                'existing_variant': {
                    'variant_id': existing_variant[0],
                    'name': existing_variant[1]
                }
            }), 409
        
        # Insert variant data
        cursor.execute('''
            INSERT INTO variants (
                product_id, user_id, name, price, description, stock
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['product_id'],
            user_id,
            data['name'].strip(),
            data['price'],
            data.get('description', '').strip() if data.get('description') else None,
            data.get('stock', 0)
        ))
        
        # Get the inserted variant ID
        variant_id = cursor.lastrowid
        
        # Commit and close connection
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product variant added successfully',
            'status': 'success',
            'variant_id': variant_id,
            'product_id': data['product_id'],
            'user_id': user_id,
            'data': {
                'variant_id': variant_id,
                'product_id': data['product_id'],
                'name': data['name'].strip(),
                'price': data['price'],
                'description': data.get('description', '').strip() if data.get('description') else None,
                'stock': data.get('stock', 0)
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


@product_variants_bp.route('/variant/<int:variant_id>', methods=['PUT'])
@token_required
def update_product_variant(variant_id):
    """Update a specific variant"""
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
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'validation_error'
            }), 400
        
        # Connect to variants database
        conn = sqlite3.connect('variants.db')
        cursor = conn.cursor()
        
        # Verify variant exists and belongs to user
        cursor.execute('''
            SELECT variant_id, product_id, name, price, description, stock 
            FROM variants 
            WHERE variant_id = ? AND user_id = ?
        ''', (variant_id, user_id))
        
        existing_variant = cursor.fetchone()
        if not existing_variant:
            conn.close()
            return jsonify({
                'error': 'Variant not found or does not belong to this user',
                'status': 'variant_not_found'
            }), 404
        
        # Prepare update data
        update_fields = []
        update_values = []
        
        # Check which fields to update
        if 'name' in data and data['name']:
            if len(data['name'].strip()) < 2:
                conn.close()
                return jsonify({
                    'error': 'Variant name must be at least 2 characters long',
                    'status': 'validation_error'
                }), 400
            
            # Check for duplicate name (excluding current variant)
            cursor.execute('''
                SELECT variant_id FROM variants 
                WHERE LOWER(name) = LOWER(?) AND product_id = ? AND user_id = ? AND variant_id != ?
            ''', (data['name'].strip(), existing_variant[1], user_id, variant_id))
            
            if cursor.fetchone():
                conn.close()
                return jsonify({
                    'error': f'Variant with name "{data["name"]}" already exists for this product',
                    'status': 'duplicate_variant'
                }), 409
            
            update_fields.append('name = ?')
            update_values.append(data['name'].strip())
        
        if 'price' in data and data['price'] is not None:
            try:
                price = float(data['price'])
                if price < 0:
                    conn.close()
                    return jsonify({
                        'error': 'Price cannot be negative',
                        'status': 'validation_error'
                    }), 400
                update_fields.append('price = ?')
                update_values.append(price)
            except ValueError:
                conn.close()
                return jsonify({
                    'error': 'Invalid price format',
                    'status': 'validation_error'
                }), 400
        
        if 'description' in data:
            if data['description'] and len(data['description'].strip()) > 1000:
                conn.close()
                return jsonify({
                    'error': 'Description cannot exceed 1000 characters',
                    'status': 'validation_error'
                }), 400
            update_fields.append('description = ?')
            update_values.append(data['description'].strip() if data['description'] else None)
        
        if 'stock' in data and data['stock'] is not None:
            try:
                stock = int(data['stock'])
                if stock < 0:
                    conn.close()
                    return jsonify({
                        'error': 'Stock cannot be negative',
                        'status': 'validation_error'
                    }), 400
                update_fields.append('stock = ?')
                update_values.append(stock)
            except ValueError:
                conn.close()
                return jsonify({
                    'error': 'Invalid stock format',
                    'status': 'validation_error'
                }), 400
        
        if 'is_active' in data:
            update_fields.append('is_active = ?')
            update_values.append(1 if data['is_active'] else 0)
        
        if not update_fields:
            conn.close()
            return jsonify({
                'error': 'No valid fields to update',
                'status': 'validation_error'
            }), 400
        
        # Update the variant
        update_query = f'''
            UPDATE variants 
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE variant_id = ? AND user_id = ?
        '''
        update_values.extend([variant_id, user_id])
        
        cursor.execute(update_query, update_values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'error': 'Variant not found or no changes made',
                'status': 'variant_not_found'
            }), 404
        
        # Get updated variant
        cursor.execute('''
            SELECT variant_id, product_id, name, price, description, stock, is_active, updated_at
            FROM variants 
            WHERE variant_id = ? AND user_id = ?
        ''', (variant_id, user_id))
        
        updated_variant = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Variant updated successfully',
            'status': 'success',
            'variant': {
                'variant_id': updated_variant[0],
                'product_id': updated_variant[1],
                'name': updated_variant[2],
                'price': updated_variant[3],
                'description': updated_variant[4],
                'stock': updated_variant[5],
                'is_active': bool(updated_variant[6]),
                'updated_at': updated_variant[7]
            }
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


@product_variants_bp.route('/variant/<int:variant_id>', methods=['DELETE'])
@token_required
def delete_product_variant(variant_id):
    """Delete a specific variant"""
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
        
        # Get variant info before deletion
        cursor.execute('''
            SELECT variant_id, product_id, name 
            FROM variants 
            WHERE variant_id = ? AND user_id = ?
        ''', (variant_id, user_id))
        
        variant_info = cursor.fetchone()
        if not variant_info:
            conn.close()
            return jsonify({
                'error': 'Variant not found or does not belong to this user',
                'status': 'variant_not_found'
            }), 404
        
        # Delete the variant
        cursor.execute('''
            DELETE FROM variants 
            WHERE variant_id = ? AND user_id = ?
        ''', (variant_id, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'error': 'Variant not found or could not be deleted',
                'status': 'variant_not_found'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Variant deleted successfully',
            'status': 'success',
            'deleted_variant': {
                'variant_id': variant_info[0],
                'product_id': variant_info[1],
                'name': variant_info[2]
            }
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
