from flask import Flask
from apis.auth_app.seller.login_jwt import login_jwt_seller
from apis.auth_app.buyer.login_jwt import login_jwt_buyer
from apis.registration.seller.signup import signup_login_seller
from apis.registration.buyer.signup import signup_login_buyer
from apis.e_commerce.add_products import add_products_bp
from apis.e_commerce.get_products import get_products_bp
from apis.e_commerce.add_variants import product_variants_bp
from apis.e_commerce.add_payment import add_payment_buyer
from modules.registration.seller.init_db import init_db_seller
from modules.registration.buyer.init_db import init_db_buyer

def create_app():
    """create and configure the flask application"""
    app = Flask(__name__)
    
    # Register the API blueprints
    app.register_blueprint(login_jwt_seller)
    app.register_blueprint(login_jwt_buyer)
    app.register_blueprint(signup_login_seller)
    app.register_blueprint(signup_login_buyer)
    app.register_blueprint(add_products_bp)
    app.register_blueprint(get_products_bp)
    app.register_blueprint(product_variants_bp)
    app.register_blueprint(add_payment_buyer)
    
    return app

if __name__ == '__main__':
    app = create_app()
    init_db_seller()
    init_db_buyer()
    
    # Run the application
    print("🚀 Starting E-commerce API Server...")
    print("📍 Endpoints available:")
    print("   POST /login/seller - Seller login")
    print("   POST /login/buyer - Buyer login")
    print("   POST /register/seller - Seller registration")
    print("   POST /register/buyer - Buyer registration")
    print("   POST /add/products - Add a new product (requires seller JWT token)")
    print("   PUT /update/product/<id> - Update a product (requires seller JWT token)")
    print("   DELETE /delete/product/<id> - Delete a product (requires seller JWT token)")
    print("   GET /product/<id> - Get product details")
    print("   GET /products - List all products with filters")
    print("\n🔑 For protected endpoints, include: 'Authorization: Bearer <your_jwt_token>' in headers")
    print("💾 Databases: sellers.db, buyers.db, and products.db will be created automatically")
    
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5001,       # Different port from auth service
        debug=True       # Enable debug mode for development
    )

