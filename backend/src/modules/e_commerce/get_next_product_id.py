
import sqlite3

PRODUCTS_DATABASE = 'products.db'

def get_next_product_id():
    """Generate the next product ID in format Pxxx"""
    conn = sqlite3.connect(PRODUCTS_DATABASE)
    cursor = conn.cursor()
    
    # Get the highest product_id number
    cursor.execute('''
        SELECT product_id FROM products 
        WHERE product_id LIKE 'P%' 
        ORDER BY CAST(SUBSTR(product_id, 2) AS INTEGER) DESC 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        # Extract number from Pxxx format and increment
        last_num = int(result[0][1:])
        next_num = last_num + 1
    else:
        # First product
        next_num = 1
    
    return f"P{next_num:03d}"  # Format as P001, P002, etc.
