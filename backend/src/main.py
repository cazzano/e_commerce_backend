from flask import Flask
from apis.e_commerce.products_api import products_api

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Register the products API blueprint
    app.register_blueprint(products_api)
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Run the application
    print("🚀 Starting Products API Server...")
    print("📍 Endpoints available:")
    print("   POST /auth/add/products - Add a new product (requires JWT token)")
    print("   GET  /products/<product_id> - Get product by ID (requires JWT token)")
    print("🔑 Don't forget to include 'Authorization: Bearer <your_jwt_token>' in headers!")
    print("💾 Database: products.db will be created automatically")
    
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5001,       # Different port from auth service
        debug=True       # Enable debug mode for development
    )

