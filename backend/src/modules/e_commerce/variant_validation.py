def validate_variant_data(data):
    """Validate required fields and data types for product variants"""
    required_fields = ['product_id', 'name', 'price']
    
    # Check if all required fields are present
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            return False, f"Missing or empty required field: {field}"
    
    # Validate data types
    try:
        # Validate product_id
        int(data['product_id'])
        
        # Validate price
        price = float(data['price'])
        if price < 0:
            return False, "Price cannot be negative"
        
        # Validate stock if provided
        if 'stock' in data and data['stock'] is not None and str(data['stock']).strip():
            stock = int(data['stock'])
            if stock < 0:
                return False, "Stock cannot be negative"
        
        # Validate name length
        if len(data['name'].strip()) < 2:
            return False, "Variant name must be at least 2 characters long"
        
        if len(data['name'].strip()) > 255:
            return False, "Variant name cannot exceed 255 characters"
        
        # Validate description length if provided
        if 'description' in data and data['description'] and len(data['description'].strip()) > 1000:
            return False, "Description cannot exceed 1000 characters"
            
    except (ValueError, TypeError) as e:
        return False, f"Invalid data types: {str(e)}"
    
    return True, "Valid"


def validate_bulk_variants_data(variants_list):
    """Validate bulk variants data"""
    if not isinstance(variants_list, list):
        return False, "Variants data must be a list"
    
    if len(variants_list) == 0:
        return False, "Variants list cannot be empty"
    
    if len(variants_list) > 50:  # Limit bulk operations
        return False, "Cannot add more than 50 variants at once"
    
    # Validate each variant
    for i, variant in enumerate(variants_list):
        if not isinstance(variant, dict):
            return False, f"Variant at index {i} must be a dictionary"
        
        is_valid, message = validate_variant_data(variant)
        if not is_valid:
            return False, f"Variant at index {i}: {message}"
    
    # Check for duplicate variant names within the same product
    product_variants = {}
    for variant in variants_list:
        product_id = variant['product_id']
        variant_name = variant['name'].strip().lower()
        
        if product_id not in product_variants:
            product_variants[product_id] = set()
        
        if variant_name in product_variants[product_id]:
            return False, f"Duplicate variant name '{variant['name']}' found for product ID {product_id}"
        
        product_variants[product_id].add(variant_name)
    
    return True, "Valid"
