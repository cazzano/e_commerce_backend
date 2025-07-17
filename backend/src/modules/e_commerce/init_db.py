from flask import Blueprint, request, jsonify
from functools import wraps
import sqlite3
import os
import jwt
from datetime import datetime, timedelta

# Secret token for authentication
SECRET_TOKEN = "DMFGHO#$&*I)@#IUDSJIFGUI)SDR)*&#$&#@$^SDFGY@()!&@*DJSGF)#$&*#^"




# Database initialization
def init_db():
    """Initialize the products database"""
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    conn.commit()
    conn.close()


