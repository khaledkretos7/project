from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Advertisement
import json
from utils import save_multiple_files, get_image_urls

advertisements_bp = Blueprint('advertisements', __name__)

@advertisements_bp.route('', methods=['GET'])
@jwt_required()
def get_advertisements():
    advertisements = Advertisement.query.filter_by(is_deleted=False).order_by(Advertisement.created_at.desc()).all()
    
    result = []
    for ad in advertisements:
        author = User.query.get(ad.user_id)
        
        # Parse image URLs if they exist
        image_urls = []
        if ad.images:
            try:
                image_paths = json.loads(ad.images)
                image_urls = get_image_urls(image_paths)
            except json.JSONDecodeError:
                pass
        
        ad_data = {
            "id": ad.id,
            "title": ad.title,
            "content": ad.content,
            "created_at": ad.created_at.isoformat(),
            "images": image_urls,
            "price": ad.price,
            "phone_number": ad.phone_number,
            "author": {
                "id": author.id,
                "username": author.username
            } if author and not author.is_banned else {
                "id": None,
                "username": "Deleted User"
            }
        }
        result.append(ad_data)
    
    return jsonify(result), 200

@advertisements_bp.route('', methods=['POST'])
@jwt_required()
def create_advertisement():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user.is_approved and not user.is_admin:
        return jsonify({"error": "You need to be approved to create advertisements"}), 403
    
    if user.is_banned:
        return jsonify({"error": "You are banned and cannot create advertisements"}), 403
    
    # Check if the request contains form data or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle form data with files
        title = request.form.get('title')
        content = request.form.get('content')
        files = request.files.getlist('images')
        price = request.form.get('price')
        phone_number = request.form.get('phone_number')
        # Check required fields
        if not title or not title.strip():
            return jsonify({"error": "Advertisement title is required"}), 400
        
        if not content or not content.strip():
            return jsonify({"error": "Advertisement content is required"}), 400
        
        if not price:
            return jsonify({"error": "Advertisement price is required"}), 400
        
        if not phone_number or not phone_number.strip():
            return jsonify({"error": "Advertisement phone number is required"}), 400
        # Save uploaded files
        image_paths = []
        if files:
            image_paths = save_multiple_files(files)
        
        # Create new advertisement
        new_ad = Advertisement(
            title=title,
            content=content,
            user_id=current_user_id,
            price=price,
            phone_number=phone_number,
            images=json.dumps(image_paths) if image_paths else None
        )
    else:
        # Handle JSON data (no files)
        data = request.get_json()

        # Check required fields
        if 'title' not in data or not data['title'].strip():
            return jsonify({"error": "Advertisement title is required"}), 400
        
        if 'content' not in data or not data['content'].strip():
            return jsonify({"error": "Advertisement content is required"}), 400
        
        if 'price' not in data:
            return jsonify({"error": "Advertisement price is required"}), 400
        
        if 'phone_number' not in data or not data['phone_number'].strip():
            return jsonify({"error": "Advertisement phone number is required"}), 400

        # Create new advertisement
        new_ad = Advertisement(
            title=data['title'],
            content=data['content'],
            user_id=current_user_id,
            price=data.get('price'),
            phone_number=data.get('phone_number'),
            images=json.dumps(data.get('images', [])) if data.get('images') else None
        )
    
    db.session.add(new_ad)
    db.session.commit()
    
    # Get image URLs for response
    image_urls = []
    if new_ad.images:
        try:
            image_paths = json.loads(new_ad.images)
            image_urls = get_image_urls(image_paths)
        except json.JSONDecodeError:
            pass
    
    return jsonify({
        "message": "Advertisement created successfully",
        "advertisement": {
            "id": new_ad.id,
            "title": new_ad.title,
            "content": new_ad.content,
            "created_at": new_ad.created_at.isoformat(),
            "images": image_urls,
            "price": new_ad.price,
            "phone_number": new_ad.phone_number,
            "author": {
                "id": user.id,
                "username": user.username
            }
        }
    }), 201

@advertisements_bp.route('/<int:ad_id>', methods=['DELETE'])
@jwt_required()
def delete_advertisement(ad_id):
    current_user_id = int(get_jwt_identity())
    is_admin = User.query.get(current_user_id).is_admin
    
    ad = Advertisement.query.get(ad_id)
    
    
    if not ad:
        return jsonify({"error": "Advertisement not found"}), 404
    
    # Only ad author or admin can delete an ad
    if ad.user_id != current_user_id and not is_admin:
        return jsonify({"error": "Unauthorized to delete this advertisement"}), 403
    
    # If admin is deleting, mark as deleted rather than removing from database
    if is_admin and ad.user_id != current_user_id:
        ad.is_deleted = True
        db.session.commit()
        return jsonify({"message": "Advertisement marked as deleted by admin"}), 200
    
    # If it's the author deleting their own ad
    db.session.delete(ad)
    db.session.commit()
    
    return jsonify({"message": "Advertisement deleted successfully"}), 200

@advertisements_bp.route('/<int:ad_id>', methods=['PUT'])
@jwt_required()
def update_advertisement(ad_id):
    current_user_id = int(get_jwt_identity())
    
    ad = Advertisement.query.get(ad_id)
    
    if not ad:
        return jsonify({"error": "Advertisement not found"}), 404
    
    # Only ad author can update an ad
    if ad.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to update this advertisement"}), 403
    
    if ad.is_deleted:
        return jsonify({"error": "Cannot update a deleted advertisement"}), 400
    
    # Check if the request contains form data or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle form data with files
        title = request.form.get('title')
        content = request.form.get('content')
        files = request.files.getlist('images')
        keep_existing_images = request.form.get('keepExistingImages') == 'true'
        price = request.form.get('price')
        phone_number = request.form.get('phone_number')
        # Update fields if provided
        if title and title.strip():
            ad.title = title
        
        if content and content.strip():
            ad.content = content
        
        # Handle images
        if files:
            # Save new uploaded files
            new_image_paths = save_multiple_files(files)
            
            # If keeping existing images, merge with existing ones
            if keep_existing_images and ad.images:
                try:
                    existing_paths = json.loads(ad.images)
                    all_paths = existing_paths + new_image_paths
                    ad.images = json.dumps(all_paths)
                except json.JSONDecodeError:
                    ad.images = json.dumps(new_image_paths)
            else:
                ad.images = json.dumps(new_image_paths)
        elif not keep_existing_images:
            # If not keeping existing images and no new ones uploaded, clear images
            ad.images = None
    else:
        # Handle JSON data
        data = request.get_json()
        
        # Update fields if provided
        if 'title' in data and data['title'].strip():
            ad.title = data['title']
        
        if 'content' in data and data['content'].strip():
            ad.content = data['content']
        
        # Update images if provided
        if 'images' in data:
            ad.images = json.dumps(data['images']) if data['images'] else None
    
    db.session.commit()
    
    # Get image URLs for response
    image_urls = []
    if ad.images:
        try:
            image_paths = json.loads(ad.images)
            image_urls = get_image_urls(image_paths)
        except json.JSONDecodeError:
            pass
    
    return jsonify({
        "message": "Advertisement updated successfully",
        "advertisement": {
            "id": ad.id,
            "title": ad.title,
            "content": ad.content,
            "images": image_urls,
            "created_at": ad.created_at.isoformat(),
            "price": ad.price,
            "phone_number": ad.phone_number,
            "author": {
                "id": ad.user_id,
                "username": ad.author.username
            }
        }
    }), 200
