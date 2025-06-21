from app import app, db
from models import User
import bcrypt
import os

def init_database():
    with app.app_context():
        # Check if admin user exists
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            # Create admin user
            hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
            admin_user = User(
                username='admin',
                password=hashed_password.decode('utf-8'),
                full_name='Admin User',
                building_number='N/A',
                apartment_number='N/A',
                is_admin=True,
                is_approved=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")

if __name__ == '__main__':
    init_database()
