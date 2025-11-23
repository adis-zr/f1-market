"""Authentication routes and logic."""
import re
import random
import requests
from flask import Blueprint, request, jsonify, session, current_app
from db import db, User, UserRole, OTP
from config import is_mailgun_configured
from datetime import datetime, timedelta

bp = Blueprint('auth', __name__)


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))


def send_otp_email(email: str, otp_code: str, mailgun_configured: bool) -> bool:
    """Send OTP via Mailgun."""
    if not mailgun_configured:
        print(f"[DEBUG] Would send OTP {otp_code} to {email} (Mailgun not configured)")
        return False

    try:
        api_key = current_app.config['MAILGUN_API_KEY']
        domain = current_app.config['MAILGUN_DOMAIN']
        from_email = current_app.config['MAILGUN_FROM_EMAIL']

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
                "text": text,
            },
            timeout=10,
        )
        if response.status_code != 200:
            print(f"[MAILGUN] Error {response.status_code}: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


@bp.route('/request-otp', methods=['POST'])
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
            expires_at=expires_at,
        )
        new_otp.set_code(otp_code)

        db.session.add(new_otp)
        db.session.commit()

        # Send OTP via email
        mailgun_configured = is_mailgun_configured(current_app)
        email_sent = send_otp_email(email, otp_code, mailgun_configured)

        if not email_sent and mailgun_configured:
            return jsonify({'message': 'Failed to send OTP email. Please check Mailgun configuration.'}), 500

        return jsonify({
            'message': 'OTP sent to your email' if email_sent else 'OTP generated (check console for debug)',
            'email': email,
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in request_otp: {e}")
        return jsonify({'message': 'Server error occurred'}), 500


@bp.route('/verify-otp', methods=['POST'])
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
            used=False,
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
            user = User(
                email=email,
                username=email.split('@')[0],
                role=UserRole.PLAYER.value,
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
            'role': user.role,
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in verify_otp: {e}")
        return jsonify({'message': 'Server error occurred'}), 500


@bp.route('/me', methods=['GET'])
def get_current_user():
    """Get the current logged-in user from session."""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({
                'email': user.email,
                'username': user.username,
                'role': user.role,
                'logged_in': True,
            }), 200

    return jsonify({'logged_in': False}), 200


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout the current user by clearing the session."""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

