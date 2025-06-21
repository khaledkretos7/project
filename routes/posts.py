from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, Post, User
from socket_instance import socketio

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('', methods=['GET'])
@jwt_required()
def get_posts():
    try:
        # Get user ID from JWT identity (now a string)
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500
    
    if not user.is_approved and not user.is_admin:
        return jsonify({"error": "You need to be approved to view posts"}), 403
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    
    result = []
    for post in posts:
        author = User.query.get(post.user_id)
        # Determine the content based on deletion status and type
        content = post.content
        if post.is_deleted:
            if post.deletion_type == 'admin':
                content = "This message was deleted by an admin"
            else:  # user deleted
                content = "This message was deleted"
                
        post_data = {
            "id": post.id,
            "content": content,
            "created_at": post.created_at.isoformat(),
            "is_deleted": post.is_deleted,
            "deletion_type": post.deletion_type if post.is_deleted else None,
            "author": {
                "id": author.id,
                "username": author.username,
                "is_banned": author.is_banned
            } if author and not author.is_banned else {
                "id": None,
                "username": "Deleted User",
                "is_banned": True
            }
        }
        result.append(post_data)
    
    return jsonify(result), 200

@posts_bp.route('', methods=['POST'])
@jwt_required()
def create_post():
    try:
        # Get user ID from JWT identity (now a string)
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500
    
    if not user.is_approved and not user.is_admin:
        return jsonify({"error": "You need to be approved to create posts"}), 403
    
    if user.is_banned:
        return jsonify({"error": "You are banned and cannot create posts"}), 403
    
    data = request.get_json()
    
    if 'content' not in data or not data['content'].strip():
        return jsonify({"error": "Post content is required"}), 400
    
    new_post = Post(
        content=data['content'],
        user_id=int(current_user_id)
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    # Prepare post data for real-time update
    post_data = {
        "id": new_post.id,
        "content": new_post.content,
        "created_at": new_post.created_at.isoformat(),
        "author": {
            "id": user.id,
            "username": user.username
        }
    }
    
    # Emit the new post to all connected clients
    socketio.emit('post_update', post_data)
    
    return jsonify({
        "message": "Post created successfully",
        "post": {
            "id": new_post.id,
            "content": new_post.content,
            "created_at": new_post.created_at.isoformat(),
            "author": {
                "id": user.id,
                "username": user.username
            }
        }
    }), 201

@posts_bp.route('/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    try:
        # Get user ID from JWT identity (now a string)
        current_user_id = int(get_jwt_identity())
        # Get admin status from JWT claims
        claims = get_jwt()
        is_admin = claims.get('is_admin', False)
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500
    
    post = Post.query.get(post_id)
    
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    # Only post author or admin can delete a post
    if post.user_id != int(current_user_id) and not is_admin:
        return jsonify({"error": "Unauthorized to delete this post"}), 403
    
    # Mark the post as deleted and set the deletion type
    post.is_deleted = True
    
    # If admin is deleting someone else's post
    if is_admin and post.user_id != int(current_user_id):
        post.deletion_type = 'admin'
        db.session.commit()
        
        # Get author info for the response
        author = User.query.get(post.user_id)
        
        # Emit socket event for post update with complete post data
        post_data = {
            "id": post.id,
            "content": "This message was deleted by an admin",
            "created_at": post.created_at.isoformat(),
            "is_deleted": True,
            "deletion_type": 'admin',
            "author": {
                "id": author.id,
                "username": author.username,
                "is_banned": author.is_banned
            } if author and not author.is_banned else {
                "id": None,
                "username": "Deleted User",
                "is_banned": True
            }
        }
        socketio.emit('post_update', post_data)
        
        return jsonify({"message": "Post marked as deleted by admin"}), 200
    
    # If it's the author deleting their own post
    post.deletion_type = 'user'
    db.session.commit()
    
    # Get author info for the response
    author = User.query.get(post.user_id)
    
    # Emit socket event for post update with complete post data
    post_data = {
        "id": post.id,
        "content": "This message was deleted",
        "created_at": post.created_at.isoformat(),
        "is_deleted": True,
        "deletion_type": 'user',
        "author": {
            "id": author.id,
            "username": author.username,
            "is_banned": author.is_banned
        } if author and not author.is_banned else {
            "id": None,
            "username": "Deleted User",
            "is_banned": True
        }
    }
    socketio.emit('post_update', post_data)
    
    return jsonify({"message": "Post deleted successfully"}), 200
