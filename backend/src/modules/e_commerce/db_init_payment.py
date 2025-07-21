import sqlite3

def create_payment_table_if_not_exists():
    """Create payments table if it doesn't exist"""
    try:
        # Try different possible paths for the database
        possible_paths = ['buyers.db', '../buyers.db', './buyers.db']
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                print(f"Payments table created/verified at: {path}")
                return conn
                
            except Exception as e:
                if conn:
                    conn.close()
                print(f"Failed to connect to {path}: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"Error creating payments table: {e}")
        return None


