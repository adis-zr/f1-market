"""
Script to reset the database with the new schema.
This will delete the existing database and recreate it with the updated schema.
WARNING: This will delete all existing data!
"""
import os
from app import app
from db import db, User, OTP

def reset_database():
    env = os.environ.get('FLASK_ENV', 'development').lower()
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')

    if env == 'production':
        raise RuntimeError("Refusing to run in production environment")

    print(f"Environment: {env}")
    print(f"Database URL: {db_url}")

    """Delete and recreate the database with the new schema."""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    with app.app_context():
        # Drop all tables
        print(f"Dropping existing tables (environment: {env})...")
        db.drop_all()
        
        # Create all tables with the new schema
        print("Creating tables with new schema...")
        db.create_all()
        
        print("Database reset complete!")
        print("The database now has the updated schema with:")
        print("  - User.email (required, unique)")
        print("  - User.username (optional, not unique)")
        print("  - OTP.code_hash (hashed OTP codes)")

if __name__ == "__main__":
    response = input("This will delete all existing data. Continue? (yes/no): ")
    if response.lower() == 'yes':
        reset_database()
    else:
        print("Cancelled.")

