from flask import Blueprint, request, jsonify
from functools import wraps
import sqlite3
import os
import jwt
import hashlib
from datetime import datetime, timedelta

# Secret token for authentication
SECRET_TOKEN = "DMFGHO#$&*I)@#IUDSJIFGUI)SDR)*&#$&#@$^SDFGY@()!&@*DJSGF)#$&*#^"


def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    """Initialize the products database with user_id for multi-seller support"""
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    # Create products table with user_id for seller isolation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            incoming INTEGER DEFAULT 0,
            category_type TEXT NOT NULL,
            category_name TEXT NOT NULL,
            sub_category TEXT,
            brand TEXT,
            description TEXT,
            specifications TEXT,
            delivery_charges REAL DEFAULT 0.0,
            delivery_day INTEGER DEFAULT 1,
            discounts REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index for better performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_user_id 
        ON products (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_user_name 
        ON products (user_id, name)
    ''')
    
    conn.commit()
    conn.close()


def create_seller(username, password, email=None, store_name=None, contact_info=None):
    """Create a new seller account"""
    try:
        # Initialize database if it doesn't exist
        if not os.path.exists('products.db'):
            init_db()
        
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT seller_id FROM sellers WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return False, "Username already exists"
        
        # Hash password and insert seller
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO sellers (username, password_hash, email, store_name, contact_info)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, email, store_name, contact_info))
        
        seller_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return True, seller_id
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"


def authenticate_seller(username, password):
    """Authenticate seller and return JWT token"""
    try:
        # Initialize database if it doesn't exist
        if not os.path.exists('products.db'):
            init_db()
        
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # Get seller data
        cursor.execute('''
            SELECT seller_id, password_hash, is_active 
            FROM sellers 
            WHERE username = ?
        ''', (username,))
        
        seller = cursor.fetchone()
        conn.close()
        
        if not seller:
            return False, "Invalid username or password"
        
        seller_id, stored_hash, is_active = seller
        
        if not is_active:
            return False, "Account is deactivated"
        
        # Verify password
        if hash_password(password) != stored_hash:
            return False, "Invalid username or password"
        
        # Generate JWT token
        payload = {
            'seller_id': seller_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
        }
        
        token = jwt.encode(payload, SECRET_TOKEN, algorithm='HS256')
        
        return True, token
        
    except Exception as e:
        return False, f"Authentication error: {str(e)}"
