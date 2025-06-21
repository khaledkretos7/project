import os
import json
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Save an uploaded file and return the path"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    filename = secure_filename(file.filename)
    # Generate a unique filename to prevent overwriting
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)
    return file_path

def save_multiple_files(files):
    """Save multiple uploaded files and return a list of paths"""
    paths = []
    for file in files:
        if file and allowed_file(file.filename):
            path = save_uploaded_file(file)
            paths.append(path)
    return paths

def get_image_urls(image_paths):
    """Convert image paths to URLs that can be accessed from the frontend"""
    if not image_paths:
        return []
    
    # If image_paths is a JSON string, parse it
    if isinstance(image_paths, str):
        try:
            image_paths = json.loads(image_paths)
        except json.JSONDecodeError:
            return []
    
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    return [f"{base_url}/{path}" for path in image_paths]
