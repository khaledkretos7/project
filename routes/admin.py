from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, User, Post, Advertisement
from socket_instance import socketio

admin_bp = Blueprint('admin', __name__)

# Admin middleware to check if user is an admin
def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        # Get user ID from identity and claims from JWT
        user_id = int(get_jwt_identity())
        claims = get_jwt()
        
        # Check if user is admin from claims
        if not claims.get('is_admin', False):
            return jsonify({"error": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@admin_bp.route('/pending-users', methods=['GET'])
@admin_required
def get_pending_users():
    users = User.query.filter_by(is_approved=False, is_banned=False).all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "building_number": user.building_number,
            "apartment_number": user.apartment_number,
            "created_at": user.created_at.isoformat()
        })
    
    return jsonify(result), 200

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if user.is_approved:
        return jsonify({"error": "User is already approved"}), 400
    
    user.is_approved = True
    db.session.commit()
    
    # Emit WebSocket event for user approval
    socketio.emit('user_status_changed', {'user_id': user.id, 'status': 'approved'})
    
    return jsonify({"message": f"User {user.username} has been approved"}), 200

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if user.is_approved:
        return jsonify({"error": "Cannot reject an already approved user"}), 400
    
    # Store username before deletion for the response message
    username = user.username
    user_id = user.id
    
    db.session.delete(user)
    db.session.commit()
    
    # Emit WebSocket event for user rejection
    socketio.emit('user_status_changed', {'user_id': user_id, 'status': 'rejected'})
    
    return jsonify({"message": f"User {username} has been rejected and deleted"}), 200

@admin_bp.route('/users/<int:user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if user.is_admin:
        return jsonify({"error": "Cannot ban an admin user"}), 400
    
    if user.is_banned:
        return jsonify({"error": "User is already banned"}), 400
    
    user.is_banned = True
    db.session.commit()
    
    # Emit WebSocket event for user ban
    socketio.emit('user_status_changed', {'user_id': user.id, 'status': 'banned'})
    
    return jsonify({"message": f"User {user.username} has been banned"}), 200

@admin_bp.route('/users/<int:user_id>/unban', methods=['POST'])
@admin_required
def unban_user(user_id):
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if not user.is_banned:
        return jsonify({"error": "User is not banned"}), 400
    
    user.is_banned = False
    db.session.commit()
    
    # Emit WebSocket event for user unban
    socketio.emit('user_status_changed', {'user_id': user.id, 'status': 'unbanned'})
    
    return jsonify({"message": f"User {user.username} has been unbanned"}), 200

@admin_bp.route('/posts/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    post = Post.query.get(post_id)
    
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    if post.is_deleted:
        return jsonify({"error": "Post is already deleted"}), 400
    
    post.is_deleted = True
    db.session.commit()
    
    return jsonify({"message": "Post has been marked as deleted"}), 200

@admin_bp.route('/advertisements/<int:ad_id>/delete', methods=['POST'])
@admin_required
def delete_advertisement(ad_id):
    ad = Advertisement.query.get(ad_id)
    
    if not ad:
        return jsonify({"error": "Advertisement not found"}), 404
    
    if ad.is_deleted:
        return jsonify({"error": "Advertisement is already deleted"}), 400
    
    ad.is_deleted = True
    db.session.commit()
    
    return jsonify({"message": "Advertisement has been marked as deleted"}), 200

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    users = User.query.all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "building_number": user.building_number,
            "apartment_number": user.apartment_number,
            "is_admin": user.is_admin,
            "is_approved": user.is_approved,
            "is_banned": user.is_banned,
            "created_at": user.created_at.isoformat()
        })
    
    return jsonify(result), 200
