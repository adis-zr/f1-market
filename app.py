"""Main Flask application."""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from db import db
from config import create_app_config
from api import bp as main_bp
from api.f1_routes import bp as f1_bp
from api.market_routes import bp as market_bp
from api.settlement_routes import bp as settlement_bp
from api.browse_routes import bp as browse_bp
from api.replay_routes import bp as replay_bp
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

# CORS configuration - allow credentials for session cookies
# Set CORS_ORIGINS env var (comma-separated) to restrict origins
# In production, CORS_ORIGINS is required for security
cors_origins = os.environ.get('CORS_ORIGINS')
flask_env = os.environ.get('FLASK_ENV', 'development').lower()

if cors_origins:
    CORS(app, supports_credentials=True, origins=[origin.strip() for origin in cors_origins.split(',')])
elif flask_env == 'production':
    raise RuntimeError("CORS_ORIGINS must be set in production for security")
else:
    CORS(app, supports_credentials=True)  # Allow all origins in development only

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[],  # No default limits; apply per-route
)

# Custom error handler for rate limit exceeded
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors."""
    return jsonify({
        'message': 'Rate limit exceeded. Please try again later.',
        'error': 'rate_limit_exceeded'
    }), 429

# Initialize database
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Register routes
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(f1_bp)
app.register_blueprint(market_bp)
app.register_blueprint(settlement_bp)
app.register_blueprint(browse_bp)
app.register_blueprint(replay_bp)

# Import auth routes to apply rate limiting
from auth.routes import apply_rate_limits
apply_rate_limits(limiter)


@app.route('/health')
def health():
    """Health check endpoint for deployment monitoring."""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
