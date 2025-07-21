from flask import jsonify, Blueprint, request
import sqlite3
from datetime import datetime, timezone
from modules.e_commerce.token_required import token_required
from modules.e_commerce.db_init_payment import create_payment_table_if_not_exists

add_payment_buyer = Blueprint('add_payment_buyer', __name__)

@add_payment_buyer.route('/add/payment', methods=['POST'])
@token_required
def add_payment(current_user):
    """Add payment information for the authenticated user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['payment_id', 'name', 'payment_type', 'card_number', 'expiry_date', 'cvv_number']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Extract payment information
        payment_id = data['payment_id']
        name = data['name']
        payment_type = data['payment_type']
        card_number = data['card_number']
        expiry_date = data['expiry_date']
        cvv_number = data['cvv_number']
        
        # Get user information from token
        user_id = current_user['user_id']
        username = current_user['username']
        
        # Validate payment type
        valid_payment_types = ['credit_card', 'debit_card', 'visa', 'mastercard', 'american_express', 'paypal']
        if payment_type.lower() not in valid_payment_types:
            return jsonify({
                'error': f'Invalid payment type. Valid types: {", ".join(valid_payment_types)}'
            }), 400
        
        # Validate card number (basic validation - should be digits and appropriate length)
        if not card_number.replace(' ', '').isdigit():
            return jsonify({'error': 'Card number must contain only digits'}), 400
        
        card_number_clean = card_number.replace(' ', '')
        if len(card_number_clean) < 13 or len(card_number_clean) > 19:
            return jsonify({'error': 'Card number must be between 13 and 19 digits'}), 400
        
        # Validate expiry date format (MM/YY or MM/YYYY)
        if '/' not in expiry_date:
            return jsonify({'error': 'Expiry date must be in MM/YY or MM/YYYY format'}), 400
        
        # Validate CVV (3 or 4 digits)
        if not cvv_number.isdigit() or len(cvv_number) not in [3, 4]:
            return jsonify({'error': 'CVV must be 3 or 4 digits'}), 400
        
        # Connect to database and insert payment information
        conn = create_payment_table_if_not_exists()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if payment_id already exists
            cursor.execute("SELECT payment_id FROM payments WHERE payment_id = ?", (payment_id,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Payment ID already exists'}), 409
            
            # Insert payment information
            cursor.execute('''
                INSERT INTO payments (payment_id, user_id, username, name, payment_type, 
                                    card_number, expiry_date, cvv_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (payment_id, user_id, username, name, payment_type, 
                  card_number, expiry_date, cvv_number))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'message': 'Payment information added successfully!',
                'payment_details': {
                    'payment_id': payment_id,
                    'user_id': user_id,
                    'username': username,
                    'name': name,
                    'payment_type': payment_type,
                    'card_last_4': card_number[-4:],  # Only show last 4 digits for security
                    'expiry_date': expiry_date,
                    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                }
            }), 201
            
        except sqlite3.IntegrityError as e:
            conn.close()
            if 'UNIQUE constraint failed' in str(e):
                return jsonify({'error': 'Payment ID already exists'}), 409
            else:
                return jsonify({'error': 'Database integrity error'}), 500
                
    except Exception as e:
        print(f"Add payment error: {e}")
        return jsonify({'error': 'An error occurred while adding payment information'}), 500

# Optional: Get user's payment methods
@add_payment_buyer.route('/get/payments', methods=['GET'])
@token_required
def get_user_payments(current_user):
    """Get all payment methods for the authenticated user"""
    try:
        user_id = current_user['user_id']
        
        # Try different possible paths for the database
        possible_paths = ['buyers.db', '../buyers.db', './buyers.db']
        conn = None

        for path in possible_paths:
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                # Test if the payments table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
                if cursor.fetchone():
                    break
                conn.close()
                conn = None
            except:
                if conn:
                    conn.close()
                continue

        if not conn:
            return jsonify({'error': 'Payments database not found'}), 404

        cursor = conn.cursor()
        cursor.execute('''
            SELECT payment_id, name, payment_type, card_number, expiry_date, created_at
            FROM payments 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        payments = cursor.fetchall()
        conn.close()
        
        # Format response with masked card numbers
        payment_list = []
        for payment in payments:
            payment_list.append({
                'payment_id': payment[0],
                'name': payment[1],
                'payment_type': payment[2],
                'card_last_4': payment[3][-4:],  # Only show last 4 digits
                'expiry_date': payment[4],
                'created_at': payment[5]
            })
        
        return jsonify({
            'user_id': user_id,
            'username': current_user['username'],
            'payments': payment_list,
            'total_payments': len(payment_list)
        }), 200
        
    except Exception as e:
        print(f"Get payments error: {e}")
        return jsonify({'error': 'An error occurred while retrieving payments'}), 500
