from unicodedata import category
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import PublicServiceCategory, db, User, PublicService

public_services_bp = Blueprint('public_services', __name__)

@public_services_bp.route('', methods=['GET'])
@jwt_required()
def get_public_services():
    public_service_categories = PublicServiceCategory.query.all()
    
    result = []
    for category in public_service_categories:
        services = PublicService.query.filter_by(category=category.id).all()
        result.append({
            "name": category.name,
            "description": category.description,
            "id":category.id,
            "services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "phone_number": service.phone_number,
                    "category":service.category,
                    "status": service.status,
                    "created_at": service.created_at.isoformat(),
                    "updated_at": service.updated_at.isoformat()
                }
                for service in services
            ]
        })
   
    
    return jsonify(result), 200

@public_services_bp.route('', methods=['POST'])
@jwt_required()
def create_public_service():
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    
    # Only admins can create public services
    if not claims.get('is_admin', False):
        return jsonify({"error": "Admin privileges required"}), 403
    
    data = request.get_json()
    
    # Check required fields
    required_fields = ['name', 'phone_number', 'status']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({"error": f"{field} is required"}), 400
    
    category = PublicServiceCategory.query.get(data['category'])
    if not category:
        return jsonify({"error": "Category not found"}), 404
    
    new_service = PublicService(
        name=data['name'],
        category=category.id,
        phone_number=data['phone_number'],
        status=data['status']
    )
    
    db.session.add(new_service)
    db.session.commit()
    
    return jsonify({
        "message": "Public service created successfully",
        "service": {
            "id": new_service.id,
            "name": new_service.name,
            "category": new_service.category,
            "phone_number": new_service.phone_number,
            "status": new_service.status,
            "created_at": new_service.created_at.isoformat(),
            "updated_at": new_service.updated_at.isoformat()
        }
    }), 201

@public_services_bp.route('/categories', methods=['GET'])
def get_public_service_categories():
    categories = PublicServiceCategory.query.all()
    
    result = []
    for category in categories:
        result.append({
            "id": category.id,
            "name": category.name,
            "description": category.description
        })
    
    return jsonify(result), 200

@public_services_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_public_service_category():
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    
    # Only admins can create categories
    if not claims.get('is_admin', False):
        return jsonify({"error": "Admin privileges required"}), 403
    
    data = request.get_json()
    
    # Check required fields
    required_fields = ['name', 'description']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({"error": f"{field} is required"}), 400
    
    new_category = PublicServiceCategory(
        name=data['name'],
        description=data['description']
    )
    
    db.session.add(new_category)
    db.session.commit()
    
    return jsonify({
        "message": "Public service category created successfully",
        "category": {
            "id": new_category.id,
            "name": new_category.name,
            "description": new_category.description,
            "created_at": new_category.created_at.isoformat(),
            "updated_at": new_category.updated_at.isoformat()
        }
    }), 201

@public_services_bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_public_service_category(category_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    
    # Only admins can update categories
    if not claims.get('is_admin', False):
        return jsonify({"error": "Admin privileges required"}), 403
    
    category = PublicServiceCategory.query.get(category_id)
    
    if not category:
        return jsonify({"error": "Public service category not found"}), 404
    
    data = request.get_json()
    print(data)
    # Update fields if provided
    if 'name' in data and data['name'].strip():
        category.name = data['name']
    
    if 'description' in data and data['description'].strip():
        category.description = data['description']
    
    db.session.commit()
    
    return jsonify({
        "message": "Public service category updated successfully",
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "created_at": category.created_at.isoformat(),
            "updated_at": category.updated_at.isoformat()
        }
    }), 200

@public_services_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_public_service_category(category_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    
    # Only admins can delete categories
    if not claims.get('is_admin', False):
        return jsonify({"error": "Admin privileges required"}), 403
    
    category = PublicServiceCategory.query.get(category_id)
    
    if not category:
        return jsonify({"error": "Public service category not found"}), 404
    
    db.session.delete(category)
    db.session.commit()
    
    return jsonify({"message": "Public service category deleted successfully"}), 200


@public_services_bp.route('/<int:service_id>', methods=['PUT'])
@jwt_required()
def update_public_service(service_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    
    # Only admins can update public services
    if not claims.get('is_admin', False):
        return jsonify({"error": "Admin privileges required"}), 403
    
    service = PublicService.query.get(service_id)
    
    if not service:
        return jsonify({"error": "Public service not found"}), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if 'name' in data and data['name'].strip():
        service.name = data['name']
    
    if 'category' in data:
        category = PublicServiceCategory.query.get(data['category'])
        if not category:
            return jsonify({"error": "Category not found"}), 404
        service.category = category.id
    
    if 'phone_number' in data and data['phone_number'].strip():
        service.phone_number = data['phone_number']
    
    if 'status' in data and data['status'].strip():
        service.status = data['status']
    
    db.session.commit()
    
    return jsonify({
        "message": "Public service updated successfully",
        "service": {
            "id": service.id,
            "name": service.name,
            "category": category.id,
            "phone_number": service.phone_number,
            "status": service.status,
            "created_at": service.created_at.isoformat(),
            "updated_at": service.updated_at.isoformat()
        }
    }), 200

@public_services_bp.route('/<int:service_id>', methods=['DELETE'])
@jwt_required()
def delete_public_service(service_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    
    # Only admins can delete public services
    if not claims.get('is_admin', False):
        return jsonify({"error": "Admin privileges required"}), 403
    
    service = PublicService.query.get(service_id)
    
    if not service:
        return jsonify({"error": "Public service not found"}), 404
    
    db.session.delete(service)
    db.session.commit()
    
    return jsonify({"message": "Public service deleted successfully"}), 200
