"""Main Flask application."""
from flask import Flask
from flask_cors import CORS
from db import db
from config import create_app_config
from api import bp as main_bp
from auth import bp as auth_bp

app = Flask(__name__)

# Configure the application
create_app_config(app)

# CORS configuration - allow credentials for session cookies
# In development, allow all origins. In production, you can restrict to specific domains.
CORS(app, supports_credentials=True)

# Initialize database
db.init_app(app)

# Create tables (fine for early dev; later you'll likely move to migrations)
with app.app_context():
    db.create_all()

# Register routes
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
