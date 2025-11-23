"""
Script to initialize the database with some default users.
Note: With OTP-based authentication, users are created automatically on first login.
This script can be used to pre-create users if needed.
"""
from app import app
from db import db, User, UserRole


def init_users():
    """Create initial users if they don't exist."""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Default users to create (with email addresses)
        default_users = [
            {"email": "admin@example.com", "username": "admin", "role": UserRole.ADMIN.value},
            {"email": "user@example.com",  "username": "user",  "role": UserRole.PLAYER.value},
            {"email": "test@example.com",  "username": "test",  "role": UserRole.PLAYER.value},
        ]
        
        for user_data in default_users:
            existing_user = User.query.filter_by(email=user_data["email"]).first()
            if not existing_user:
                new_user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    role=user_data["role"],
                )
                db.session.add(new_user)
                print(f"Created user: {user_data['email']} (role: {user_data['role']})")
            else:
                print(f"User {user_data['email']} already exists, skipping...")
        
        db.session.commit()
        print("Database initialization complete!")
        print("\nNote: Users will need to use OTP login to authenticate.")


if __name__ == "__main__":
    init_users()

