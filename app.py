from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from models import db, User, UserRole, OTP
from datetime import datetime, timedelta
import os
import secrets
import random
import re
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Session configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CORS configuration - allow credentials for session cookies
# In development, allow all origins. In production, restrict to specific domains.
# Note: For file:// protocol (opening HTML directly), cookies won't work.
# The frontend should be served from a web server (e.g., python -m http.server)
CORS(app, supports_credentials=True)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "app.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mailgun configuration
app.config['MAILGUN_API_KEY'] = os.environ.get('MAILGUN_API_KEY')
app.config['MAILGUN_DOMAIN'] = os.environ.get('MAILGUN_DOMAIN')
# Default from email: if MAILGUN_DOMAIN is mg.gridstock.io, use noreply@gridstock.io
# Otherwise use noreply@{domain} or the explicitly set MAILGUN_FROM_EMAIL
mailgun_domain = os.environ.get('MAILGUN_DOMAIN', '')
if mailgun_domain.startswith('mg.'):
    default_from = f'noreply@{mailgun_domain[3:]}'  # Remove 'mg.' prefix
else:
    default_from = f'noreply@{mailgun_domain}' if mailgun_domain else 'noreply@example.com'
app.config['MAILGUN_FROM_EMAIL'] = os.environ.get('MAILGUN_FROM_EMAIL', default_from)

# Initialize database
db.init_app(app)

# Mailgun configuration check
mailgun_configured = bool(app.config['MAILGUN_API_KEY'] and app.config['MAILGUN_DOMAIN'])

# Create tables
with app.app_context():
    db.create_all()

def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp_email(email: str, otp_code: str) -> bool:
    """Send OTP via Mailgun."""
    if not mailgun_configured:
        print(f"[DEBUG] Would send OTP {otp_code} to {email} (Mailgun not configured)")
        return False
    
    try:
        api_key = app.config['MAILGUN_API_KEY']
        domain = app.config['MAILGUN_DOMAIN']
        from_email = app.config['MAILGUN_FROM_EMAIL']
        
        subject = "Your F1 Market Login Code"
        text = f"""Your one-time password (OTP) for F1 Market is: {otp_code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email."""
        
        response = requests.post(
            f"https://api.mailgun.net/v3/{domain}/messages",
            auth=("api", api_key),
            data={
                "from": from_email,
                "to": email,
                "subject": subject,
                "text": text
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/request-otp', methods=['POST'])
def request_otp():
    """Request an OTP to be sent to the user's email."""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'message': 'Email is required'}), 400
        
        if not is_valid_email(email):
            return jsonify({'message': 'Invalid email format'}), 400
        
        # Clean up expired OTPs
        expired_otps = OTP.query.filter(OTP.expires_at < datetime.utcnow()).all()
        for otp in expired_otps:
            db.session.delete(otp)
        
        # Invalidate any existing unused OTPs for this email
        existing_otps = OTP.query.filter_by(email=email, used=False).all()
        for otp in existing_otps:
            otp.used = True
        
        # Generate new OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        new_otp = OTP(
            email=email,
            expires_at=expires_at
        )
        new_otp.set_code(otp_code)
        
        db.session.add(new_otp)
        db.session.commit()
        
        # Send OTP via email
        email_sent = send_otp_email(email, otp_code)
        
        if not email_sent and mailgun_configured:
            return jsonify({'message': 'Failed to send OTP email. Please check Mailgun configuration.'}), 500
        
        return jsonify({
            'message': 'OTP sent to your email' if email_sent else 'OTP generated (check console for debug)',
            'email': email
        }), 200
            
    except Exception as e:
        db.session.rollback()
        print(f"Error in request_otp: {e}")
        return jsonify({'message': 'Server error occurred'}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and create session."""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        otp_code = data.get('otp', '').strip()
        
        if not email or not otp_code:
            return jsonify({'message': 'Email and OTP are required'}), 400
        
        # Find valid OTPs for this email (we can't filter by code since it's hashed)
        otps = OTP.query.filter_by(
            email=email,
            used=False
        ).order_by(OTP.created_at.desc()).all()
        
        # Find the matching OTP by verifying the code
        otp = None
        for candidate_otp in otps:
            if candidate_otp.is_valid() and candidate_otp.verify_code(otp_code):
                otp = candidate_otp
                break
        
        if not otp:
            return jsonify({'message': 'Invalid or expired OTP'}), 401
        
        # Mark OTP as used
        otp.used = True
        
        # Find or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            # Create new user with email
            user = User(
                email=email,
                username=email.split('@')[0],  # Use email prefix as username
                role=UserRole.PLAYER.value
            )
            db.session.add(user)
        
        db.session.commit()
        
        # Create session
        session['user_id'] = user.id
        session['email'] = user.email
        session['username'] = user.username
        session['role'] = user.role
        
        return jsonify({
            'message': 'Login successful!',
            'email': user.email,
            'username': user.username,
            'role': user.role
        }), 200
            
    except Exception as e:
        db.session.rollback()
        print(f"Error in verify_otp: {e}")
        return jsonify({'message': 'Server error occurred'}), 500

@app.route('/me', methods=['GET'])
def get_current_user():
    """Get the current logged-in user from session."""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({
                'email': user.email,
                'username': user.username,
                'role': user.role,
                'logged_in': True
            }), 200
    
    return jsonify({'logged_in': False}), 200

@app.route('/logout', methods=['POST'])
def logout():
    """Logout the current user by clearing the session."""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

