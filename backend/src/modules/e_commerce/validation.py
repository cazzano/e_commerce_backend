
# Validation function
def validate_product_data(data):
    """Validate required fields and data types"""
    required_fields = ['name', 'price', 'stock', 'category_type', 'category_name']
    
    # Check if all required fields are present
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            return False, f"Missing or empty required field: {field}"
    
    # Validate data types
    try:
        float(data['price'])
        int(data['stock'])
        if 'incoming' in data and data['incoming'] is not None and str(data['incoming']).strip():
            int(data['incoming'])
        if 'delivery_charges' in data and data['delivery_charges'] is not None and str(data['delivery_charges']).strip():
            float(data['delivery_charges'])
        if 'delivery_day' in data and data['delivery_day'] is not None and str(data['delivery_day']).strip():
            int(data['delivery_day'])
        if 'discounts' in data and data['discounts'] is not None and str(data['discounts']).strip():
            float(data['discounts'])
    except (ValueError, TypeError):
        return False, "Invalid data types for numeric fields"
    
    return True, "Valid"


