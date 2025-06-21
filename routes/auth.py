from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User
import bcrypt
from socket_instance import socketio

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if required fields are provided
    required_fields = ['username', 'password', 'full_name', 'building_number', 'apartment_number']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Check if username already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
    
    # Hash the password
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    
    # Create new user
    new_user = User(
        username=data['username'],
        password=hashed_password.decode('utf-8'),
        full_name=data['full_name'],
        building_number=data['building_number'],
        apartment_number=data['apartment_number'],
        is_admin=False,
        is_approved=False
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    # Prepare user data for WebSocket event
    user_data = {
        "id": new_user.id,
        "username": new_user.username,
        "full_name": new_user.full_name,
        "building_number": new_user.building_number,
        "apartment_number": new_user.apartment_number,
        "created_at": new_user.created_at.isoformat()
    }
    
    # Emit WebSocket event for new user registration
    socketio.emit('user_registered', user_data)
    
    return jsonify({
        "message": "Registration successful. Your account is pending approval by an admin.",
        "user_id": new_user.id
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    
    if not bcrypt.checkpw(data['password'].encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"error": "Invalid username or password"}), 401
    
    if user.is_banned:
        return jsonify({"error": "Your account has been banned"}), 403
    
    if not user.is_approved and not user.is_admin:
        return jsonify({"error": "Your account is pending approval by an admin"}), 403
    
    # Create access token with string identity and additional claims
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'is_admin': user.is_admin}
    )
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin
        }
    }), 200

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        # Get the user ID from the JWT identity (now a string)
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
    except Exception as e:
        return jsonify({"error": f"Failed to get profile: {str(e)}"}), 500
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "building_number": user.building_number,
        "apartment_number": user.apartment_number,
        "is_admin": user.is_admin,
        "is_approved": user.is_approved,
        "created_at": user.created_at.isoformat()
    }), 200
