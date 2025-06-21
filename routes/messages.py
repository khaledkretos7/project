from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, User, Message
from sqlalchemy import or_
from socket_instance import socketio

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/admin', methods=['POST'])
@jwt_required()
def message_admin():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if user.is_banned:
        return jsonify({"error": "You are banned and cannot send messages"}), 403
    
    data = request.get_json()
    
    if 'content' not in data or not data['content'].strip():
        return jsonify({"error": "Message content is required"}), 400
    
    # Find an admin to message
    admin = User.query.filter_by(is_admin=True).first()
    
    if not admin:
        return jsonify({"error": "No admin available to message"}), 404
    
    new_message = Message(
        content=data['content'],
        sender_id=current_user_id,
        recipient_id=admin.id
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # Prepare message data for real-time update
    message_data = {
        "id": new_message.id,
        "content": new_message.content,
        "created_at": new_message.created_at.isoformat(),
        "is_read": new_message.is_read,
        "sender": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin
        },
        "recipient": {
            "id": admin.id,
            "username": admin.username,
            "is_admin": admin.is_admin
        }
    }
    
    # Emit the new message to all connected clients
    socketio.emit('message_update', message_data)
    
    return jsonify({
        "message": "Message sent to admin successfully",
        "message_id": new_message.id
    }), 201

@messages_bp.route('', methods=['GET'])
@jwt_required()
def get_messages():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    # Get all messages where the current user is either the sender or recipient
    messages = Message.query.filter(
        or_(
            Message.sender_id == current_user_id,
            Message.recipient_id == current_user_id
        )
    ).order_by(Message.created_at.asc()).all()
    
    result = []
    for message in messages:
        sender = User.query.get(message.sender_id)
        recipient = User.query.get(message.recipient_id)
        if message.is_deleted:
            if message.deletion_type == 'admin':
                content = "This message was deleted by an admin"
            else:  # user deleted
                content = "This message was deleted"
        else:
            content = message.content
        result.append({
            "id": message.id,
            "content": content,
            "created_at": message.created_at.isoformat(),
            "is_read": message.is_read,
            "is_deleted": message.is_deleted,
            "deletion_type": message.deletion_type if message.is_deleted else None,
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "is_admin": sender.is_admin
            },
            "recipient": {
                "id": recipient.id,
                "username": recipient.username,
                "is_admin": recipient.is_admin
            }
        })
    
    return jsonify(result), 200

@messages_bp.route('/<int:message_id>/read', methods=['POST'])
@jwt_required()
def mark_as_read(message_id):
    current_user_id = int(get_jwt_identity())
    
    message = Message.query.get(message_id)
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    # Only the recipient can mark a message as read
    if message.recipient_id != current_user_id:
        return jsonify({"error": "Unauthorized to mark this message as read"}), 403
    
    message.is_read = True
    db.session.commit()
    
    return jsonify({"message": "Message marked as read"}), 200

@messages_bp.route('/reply/<int:user_id>', methods=['POST'])
@jwt_required()
def reply_to_user(user_id):
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    # Only admins can reply to any user
    if not current_user.is_admin:
        return jsonify({"error": "Only admins can reply to users"}), 403
    
    recipient = User.query.get(user_id)
    
    if not recipient:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    
    if 'content' not in data or not data['content'].strip():
        return jsonify({"error": "Message content is required"}), 400
    
    new_message = Message(
        content=data['content'],
        sender_id=current_user_id,
        recipient_id=user_id
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # Prepare message data for real-time update
    message_data = {
        "id": new_message.id,
        "content": new_message.content,
        "created_at": new_message.created_at.isoformat(),
        "is_read": new_message.is_read,
        "sender": {
            "id": current_user.id,
            "username": current_user.username,
            "is_admin": current_user.is_admin
        },
        "recipient": {
            "id": recipient.id,
            "username": recipient.username,
            "is_admin": recipient.is_admin
        }
    }
    
    # Emit the new message to all connected clients
    socketio.emit('message_update', message_data)
    
    return jsonify({
        "message": f"Reply sent to {recipient.username} successfully",
        "message_id": new_message.id
    }), 201

@messages_bp.route('/<int:sender_id>/<int:recipient_id>/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(sender_id, recipient_id, message_id):
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
    
    message = Message.query.get(message_id)
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    # Only message author or admin can delete a message
    if message.sender_id != int(current_user_id) and not is_admin:
        return jsonify({"error": "Unauthorized to delete this message"}), 403
    
    # Mark the message as deleted and set the deletion type
    message.is_deleted = True
    
    # If admin is deleting someone else's message
    if not is_admin:
        message.deletion_type = "user_deleted"
    else:
        message.deletion_type = "admin_deleted"
    
    db.session.commit()
    
    return jsonify({"message": "Message deleted successfully"}), 200