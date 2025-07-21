import sqlite3

def create_payment_table_if_not_exists():
    """Create payments table in separate payment.db database"""
    try:
        # Try different possible paths for the payment database
        possible_paths = ['payment.db', '../payment.db', './payment.db']
        conn = None

        for path in possible_paths:
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                
                # Create payments table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payment_id TEXT UNIQUE NOT NULL,
                        user_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        name TEXT NOT NULL,
                        payment_type TEXT NOT NULL,
                        card_number TEXT NOT NULL,
                        expiry_date TEXT NOT NULL,
                        cvv_number TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                print(f"Payments table created/verified in payment.db at: {path}")
                return conn
                
            except Exception as e:
                if conn:
                    conn.close()
                print(f"Failed to connect to payment.db at {path}: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"Error creating payments table in payment.db: {e}")
        return None

def get_payment_db_connection():
    """Get connection to payment.db database"""
    try:
        # Try different possible paths for the payment database
        possible_paths = ['payment.db', '../payment.db', './payment.db']
        conn = None

        for path in possible_paths:
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                # Test if the payments table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
                if cursor.fetchone():
                    print(f"Connected to payment.db at: {path}")
                    return conn
                conn.close()
                conn = None
            except Exception as e:
                if conn:
                    conn.close()
                print(f"Failed to connect to payment.db at {path}: {e}")
                continue

        return None
        
    except Exception as e:
        print(f"Error connecting to payment.db: {e}")
        return None
