"""Main Flask application."""
import os
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure the application
create_app_config(app)

# Handle subpath prefix for reverse proxy deployments
# If APPLICATION_ROOT is set, create a WSGI middleware to strip the prefix
application_root = os.environ.get('APPLICATION_ROOT', '').strip()
if application_root:
    # Ensure it starts with / and doesn't end with /
    if not application_root.startswith('/'):
        application_root = '/' + application_root
    application_root = application_root.rstrip('/')
    logger.info(f"APPLICATION_ROOT configured: '{application_root}'")
    
    class SubpathMiddleware:
        """WSGI middleware to handle subpath prefix."""
        def __init__(self, app, prefix):
            self.app = app
            self.prefix = prefix.rstrip('/')
            logger.info(f"SubpathMiddleware initialized with prefix: {self.prefix}")
        
        def __call__(self, environ, start_response):
            # Get the path from the request
            original_path = environ.get('PATH_INFO', '')
            script_name = environ.get('SCRIPT_NAME', '')
            
            # Check for reverse proxy headers (some proxies set these)
            forwarded_prefix = environ.get('HTTP_X_FORWARDED_PREFIX', '').strip()
            script_name_header = environ.get('HTTP_X_SCRIPT_NAME', '').strip()
            
            # Use header if available, otherwise use configured prefix
            prefix_to_use = forwarded_prefix or script_name_header or self.prefix
            
            logger.debug(
                f"PATH_INFO: {original_path}, SCRIPT_NAME: {script_name}, "
                f"X-Forwarded-Prefix: {forwarded_prefix}, X-Script-Name: {script_name_header}, "
                f"Using prefix: {prefix_to_use}"
            )
            
            # If the path starts with our prefix, strip it
            if prefix_to_use and original_path.startswith(prefix_to_use):
                new_path = original_path[len(prefix_to_use):] or '/'
                environ['PATH_INFO'] = new_path
                environ['SCRIPT_NAME'] = prefix_to_use
                logger.debug(f"Stripped prefix - new PATH_INFO: {new_path}, SCRIPT_NAME: {prefix_to_use}")
            elif prefix_to_use:
                logger.warning(f"Path {original_path} does not start with prefix {prefix_to_use}")
            
            return self.app(environ, start_response)
    
    # Wrap the app with the middleware
    app.wsgi_app = SubpathMiddleware(app.wsgi_app, application_root)
else:
    logger.warning("APPLICATION_ROOT not set - subpath middleware not active")

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
