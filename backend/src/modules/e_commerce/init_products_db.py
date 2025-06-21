
import sqlite3

PRODUCTS_DATABASE = 'products.db'

def init_products_db():
    """Initialize the products database with required table"""
    conn = sqlite3.connect(PRODUCTS_DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            discount REAL DEFAULT 0,
            rating REAL DEFAULT 0,
            shipping TEXT,
            brand TEXT,
            selling INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
