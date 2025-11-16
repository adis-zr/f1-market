"""
Script to reset the database with the new schema.
This will delete the existing database and recreate it with the updated schema.
WARNING: This will delete all existing data!
"""
import os
from app import app, db
from models import User, OTP

def reset_database():
    """Delete and recreate the database with the new schema."""
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, "app.db")
    
    with app.app_context():
        # Drop all tables
        print("Dropping existing tables...")
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
