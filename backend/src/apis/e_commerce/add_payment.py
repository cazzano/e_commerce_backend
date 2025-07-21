from flask import jsonify, Blueprint, request
import sqlite3
from datetime import datetime, timezone
from modules.e_commerce.token_required import token_required
from modules.e_commerce.db_init_payment import create_payment_table_if_not_exists, get_payment_db_connection

add_payment_buyer = Blueprint('add_payment_buyer', __name__)

@add_payment_buyer.route('/add/payment', methods=['POST'])
@token_required
def add_payment(current_user):
    """Add payment information for the authenticated user in payment.db"""
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
        if payment_type.lower() != 'paypal':  # Skip card validation for PayPal
            if not card_number.replace(' ', '').isdigit():
                return jsonify({'error': 'Card number must contain only digits'}), 400
            
            card_number_clean = card_number.replace(' ', '')
            if len(card_number_clean) < 13 or len(card_number_clean) > 19:
                return jsonify({'error': 'Card number must be between 13 and 19 digits'}), 400
        
        # Validate expiry date format (MM/YY or MM/YYYY)
        if payment_type.lower() != 'paypal':  # Skip expiry validation for PayPal
            if '/' not in expiry_date:
                return jsonify({'error': 'Expiry date must be in MM/YY or MM/YYYY format'}), 400
        
        # Validate CVV (3 or 4 digits)
        if payment_type.lower() != 'paypal':  # Skip CVV validation for PayPal
            if not cvv_number.isdigit() or len(cvv_number) not in [3, 4]:
                return jsonify({'error': 'CVV must be 3 or 4 digits'}), 400
        
        # Connect to payment.db database and insert payment information
        conn = create_payment_table_if_not_exists()
        if not conn:
            return jsonify({'error': 'Payment database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if payment_id already exists
            cursor.execute("SELECT payment_id FROM payments WHERE payment_id = ?", (payment_id,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Payment ID already exists'}), 409
            
            # Insert payment information into payment.db
            cursor.execute('''
                INSERT INTO payments (payment_id, user_id, username, name, payment_type, 
                                    card_number, expiry_date, cvv_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (payment_id, user_id, username, name, payment_type, 
                  card_number, expiry_date, cvv_number))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'message': 'Payment information added successfully to payment.db!',
                'payment_details': {
                    'payment_id': payment_id,
                    'user_id': user_id,
                    'username': username,
                    'name': name,
                    'payment_type': payment_type,
                    'card_last_4': card_number[-4:] if payment_type.lower() != 'paypal' else 'N/A',
                    'expiry_date': expiry_date,
                    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    'database': 'payment.db'
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

@add_payment_buyer.route('/get/payments', methods=['GET'])
@token_required
def get_user_payments(current_user):
    """Get all payment methods for the authenticated user from payment.db"""
    try:
        user_id = current_user['user_id']
        
        # Connect to payment.db
        conn = get_payment_db_connection()
        if not conn:
            return jsonify({'error': 'Payment database not found'}), 404

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
            payment_info = {
                'payment_id': payment[0],
                'name': payment[1],
                'payment_type': payment[2],
                'expiry_date': payment[4],
                'created_at': payment[5]
            }
            
            # Handle different payment types
            if payment[2].lower() == 'paypal':
                payment_info['card_last_4'] = 'PayPal Account'
            else:
                payment_info['card_last_4'] = payment[3][-4:]  # Only show last 4 digits
            
            payment_list.append(payment_info)
        
        return jsonify({
            'user_id': user_id,
            'username': current_user['username'],
            'payments': payment_list,
            'total_payments': len(payment_list),
            'database': 'payment.db'
        }), 200
        
    except Exception as e:
        print(f"Get payments error: {e}")
        return jsonify({'error': 'An error occurred while retrieving payments'}), 500

@add_payment_buyer.route('/delete/payment/<payment_id>', methods=['DELETE'])
@token_required
def delete_payment(current_user, payment_id):
    """Delete a specific payment method for the authenticated user"""
    try:
        user_id = current_user['user_id']
        
        # Connect to payment.db
        conn = get_payment_db_connection()
        if not conn:
            return jsonify({'error': 'Payment database not found'}), 404

        cursor = conn.cursor()
        
        # Check if payment belongs to the user
        cursor.execute("SELECT payment_id FROM payments WHERE payment_id = ? AND user_id = ?", 
                      (payment_id, user_id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Payment not found or does not belong to user'}), 404
        
        # Delete the payment
        cursor.execute("DELETE FROM payments WHERE payment_id = ? AND user_id = ?", 
                      (payment_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Payment {payment_id} deleted successfully!',
            'database': 'payment.db'
        }), 200
        
    except Exception as e:
        print(f"Delete payment error: {e}")
        return jsonify({'error': 'An error occurred while deleting payment'}), 500
