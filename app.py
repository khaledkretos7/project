from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db, User, Post, Message, PublicService, Advertisement
from socket_instance import socketio
from routes.auth import auth_bp
from routes.posts import posts_bp
from routes.admin import admin_bp
from routes.messages import messages_bp
from routes.public_services import public_services_bp
from routes.advertisements import advertisements_bp
from datetime import timedelta
import os
from dotenv import load_dotenv
import eventlet
eventlet.monkey_patch()

# Load environment variables
load_dotenv()

app = Flask(_name_)

# Configure CORS (تسمح للفرونت بالتواصل مع الباك)
CORS(app, supports_credentials=True)

# إعدادات قاعدة البيانات وغيرها
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://your-backend.onrender.com')

# تهيئة الإضافات
jwt = JWTManager(app)
db.init_app(app)
socketio.init_app(app, cors_allowed_origins="*")

# تسجيل الـ Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(posts_bp, url_prefix='/api/posts')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(messages_bp, url_prefix='/api/messages')
app.register_blueprint(public_services_bp, url_prefix='/api/public-services')
app.register_blueprint(advertisements_bp, url_prefix='/api/advertisements')

with app.app_context():
    db.create_all()

@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    print('Database tables created.')


@app.route('/')
def index():
    return jsonify({"message": "Welcome to Neighborhood Forum API"})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('new_post')
def handle_new_post(data):
    socketio.emit('post_update', data)

@socketio.on('new_message')
def handle_new_message(data):
    socketio.emit('message_update', data)

if _name_ == '_main_':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)