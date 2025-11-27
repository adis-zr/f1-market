"""Main Flask application."""
import os
import logging
from flask import Flask, jsonify
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
# Always apply middleware - it will auto-detect the prefix from headers or use APPLICATION_ROOT
class SubpathMiddleware:
    """WSGI middleware to handle subpath prefix."""
    def __init__(self, app, configured_prefix=None):
        self.app = app
        self.configured_prefix = configured_prefix.rstrip('/') if configured_prefix else None
        # Common prefixes to try if not configured
        self.common_prefixes = ['/f1-market-api', '/api']
        logger.info(f"SubpathMiddleware initialized with configured prefix: {self.configured_prefix}")
    
    def __call__(self, environ, start_response):
        # Get the path from the request
        original_path = environ.get('PATH_INFO', '')
        script_name = environ.get('SCRIPT_NAME', '')
        
        # Check for reverse proxy headers (some proxies set these)
        forwarded_prefix = environ.get('HTTP_X_FORWARDED_PREFIX', '').strip()
        script_name_header = environ.get('HTTP_X_SCRIPT_NAME', '').strip()
        
        # Determine which prefix to use (priority: headers > configured > auto-detect)
        prefix_to_use = None
        
        if forwarded_prefix:
            prefix_to_use = forwarded_prefix
            logger.info(f"Using X-Forwarded-Prefix header: {prefix_to_use}")
        elif script_name_header:
            prefix_to_use = script_name_header
            logger.info(f"Using X-Script-Name header: {prefix_to_use}")
        elif self.configured_prefix:
            prefix_to_use = self.configured_prefix
            logger.info(f"Using configured APPLICATION_ROOT: {prefix_to_use}")
        else:
            # Auto-detect: try common prefixes
            for prefix in self.common_prefixes:
                if original_path.startswith(prefix):
                    prefix_to_use = prefix
                    logger.info(f"Auto-detected prefix from path: {prefix_to_use}")
                    break
        
        # Log at INFO level so we can see what's happening in production
        logger.info(
            f"Request - PATH_INFO: '{original_path}', SCRIPT_NAME: '{script_name}', "
            f"X-Forwarded-Prefix: '{forwarded_prefix}', X-Script-Name: '{script_name_header}'"
        )
        
        # If we found a prefix and the path starts with it, strip it
        if prefix_to_use and original_path.startswith(prefix_to_use):
            new_path = original_path[len(prefix_to_use):] or '/'
            environ['PATH_INFO'] = new_path
            environ['SCRIPT_NAME'] = prefix_to_use
            logger.info(f"✓ Stripped prefix '{prefix_to_use}' - new PATH_INFO: '{new_path}', SCRIPT_NAME: '{prefix_to_use}'")
        elif prefix_to_use:
            logger.warning(f"✗ Path '{original_path}' does not start with prefix '{prefix_to_use}'")
        else:
            logger.info(f"No prefix detected or configured - using original path: '{original_path}'")
        
        return self.app(environ, start_response)

# Get configured prefix from environment
application_root = os.environ.get('APPLICATION_ROOT', '').strip()
if application_root:
    # Ensure it starts with / and doesn't end with /
    if not application_root.startswith('/'):
        application_root = '/' + application_root
    application_root = application_root.rstrip('/')
    logger.info(f"APPLICATION_ROOT configured: '{application_root}'")
else:
    logger.info("APPLICATION_ROOT not set - will auto-detect from headers or common prefixes")

# Always wrap the app with the middleware (it will handle the case when no prefix is configured)
app.wsgi_app = SubpathMiddleware(app.wsgi_app, application_root if application_root else None)

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

# Debug: Catch-all route to see what paths Flask receives (remove after debugging)
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def catch_all(path):
    """Catch-all route for debugging - shows what path Flask received."""
    from flask import request
    logger.warning(f"404 - No route matched. Path received by Flask: '{request.path}', Full URL: '{request.url}'")
    return jsonify({
        'error': 'Not Found',
        'path_received': request.path,
        'path_info': request.environ.get('PATH_INFO', ''),
        'script_name': request.environ.get('SCRIPT_NAME', ''),
        'full_url': request.url,
        'method': request.method,
    }), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)
