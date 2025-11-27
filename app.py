"""Main Flask application."""
import os
from flask import Flask
from flask_cors import CORS
from db import db
from config import create_app_config
from api import bp as main_bp
from api.f1_routes import bp as f1_bp
from api.market_routes import bp as market_bp
from api.settlement_routes import bp as settlement_bp
from api.browse_routes import bp as browse_bp
from auth import bp as auth_bp

app = Flask(__name__)

# Configure the application
create_app_config(app)

# Handle subpath prefix for reverse proxy deployments
# If APPLICATION_ROOT is set, create a WSGI middleware to strip the prefix
application_root = os.environ.get('APPLICATION_ROOT', '')
if application_root:
    # Ensure it starts with / and doesn't end with /
    application_root = '/' + application_root.strip('/')
    
    class SubpathMiddleware:
        """WSGI middleware to handle subpath prefix."""
        def __init__(self, app, prefix):
            self.app = app
            self.prefix = prefix.rstrip('/')
        
        def __call__(self, environ, start_response):
            # Get the path from the request
            path = environ.get('PATH_INFO', '')
            
            # If the path starts with our prefix, strip it
            if path.startswith(self.prefix):
                environ['PATH_INFO'] = path[len(self.prefix):] or '/'
                environ['SCRIPT_NAME'] = self.prefix
            
            return self.app(environ, start_response)
    
    # Wrap the app with the middleware
    app.wsgi_app = SubpathMiddleware(app.wsgi_app, application_root)

# CORS configuration - allow credentials for session cookies
# In development, allow all origins. In production, you can restrict to specific domains.
# Set CORS_ORIGINS env var (comma-separated) to restrict origins in production
cors_origins = os.environ.get('CORS_ORIGINS')
if cors_origins:
    CORS(app, supports_credentials=True, origins=[origin.strip() for origin in cors_origins.split(',')])
else:
    CORS(app, supports_credentials=True)  # Allow all origins (development default)

# Initialize database
db.init_app(app)

# Create tables (fine for early dev; later you'll likely move to migrations)
with app.app_context():
    db.create_all()

# Register routes
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(f1_bp)
app.register_blueprint(market_bp)
app.register_blueprint(settlement_bp)
app.register_blueprint(browse_bp)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
