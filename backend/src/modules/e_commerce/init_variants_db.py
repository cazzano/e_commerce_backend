import sqlite3
import os
from datetime import datetime


def init_variants_db():
    """Initialize the variants database with proper schema"""
    conn = sqlite3.connect('variants.db')
    cursor = conn.cursor()
    
    # Create variants table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS variants (
            variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            stock INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_variants_product_id 
        ON variants (product_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_variants_user_id 
        ON variants (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_variants_user_product 
        ON variants (user_id, product_id)
    ''')
    
    # Create trigger to update updated_at timestamp
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_variants_timestamp 
        AFTER UPDATE ON variants
        BEGIN
            UPDATE variants SET updated_at = CURRENT_TIMESTAMP WHERE variant_id = NEW.variant_id;
        END
    ''')
    
    conn.commit()
    conn.close()
    print("Variants database initialized successfully!")


def verify_product_exists(product_id, user_id):
    """Verify if a product exists for the given user"""
    try:
        # Check if products.db exists
        if not os.path.exists('products.db'):
            return False, "Products database not found"
        
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT product_id, name FROM products 
            WHERE product_id = ? AND user_id = ?
        ''', (product_id, user_id))
        
        product = cursor.fetchone()
        conn.close()
        
        if product:
            return True, product
        else:
            return False, "Product not found or doesn't belong to this user"
            
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"


if __name__ == "__main__":
    init_variants_db()
