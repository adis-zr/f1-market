"""Authentication routes and logic."""
import re
import random
import requests
import logging
from flask import Blueprint, request, jsonify, session, current_app
from db import db, User, UserRole, OTP
from config import is_mailgun_configured, is_email_allowed
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
        logger.warning(f"Mailgun not configured - would send OTP {otp_code} to {email}")
        return False

    try:
        api_key = current_app.config.get('MAILGUN_API_KEY')
        domain = current_app.config.get('MAILGUN_DOMAIN')
        from_email = current_app.config.get('MAILGUN_FROM_EMAIL')

        # Validate configuration
        if not api_key:
            logger.error("MAILGUN_API_KEY is not set")
            return False
        if not domain:
            logger.error("MAILGUN_DOMAIN is not set")
            return False
        if not from_email:
            logger.error("MAILGUN_FROM_EMAIL is not set")
            return False

        subject = "Your F1 Market Login Code"
        text = f"""Your one-time password (OTP) for F1 Market is: {otp_code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email."""

        url = f"https://api.mailgun.net/v3/{domain}/messages"
        logger.info(f"Attempting to send OTP email to {email} via Mailgun (domain: {domain})")

        response = requests.post(
            url,
            auth=("api", api_key),
            data={
                "from": from_email,
                "to": email,
                "subject": subject,
                "text": text,
            },
            timeout=10,
        )

        # Mailgun returns 200 (OK) or 202 (Accepted) for successful requests
        if response.status_code in (200, 202):
            logger.info(f"OTP email sent successfully to {email} (status: {response.status_code})")
            return True
        else:
            logger.error(
                f"Mailgun API error - Status: {response.status_code}, "
                f"Response: {response.text}, "
                f"Domain: {domain}, "
                f"From: {from_email}"
            )
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error sending email to {email}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {email}: {e}", exc_info=True)
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

        # Check if email is in allowlist
        if not is_email_allowed(current_app, email):
            return jsonify({'message': 'Email not authorized to request OTP'}), 403

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
        logger.info(f"Requesting OTP for {email} - Mailgun configured: {mailgun_configured}")
        
        email_sent = send_otp_email(email, otp_code, mailgun_configured)

        if not email_sent and mailgun_configured:
            logger.error(f"Failed to send OTP email to {email} despite Mailgun being configured")
            return jsonify({
                'message': 'Failed to send OTP email. Please check Mailgun configuration and logs.',
                'error': 'email_send_failed'
            }), 500

        if email_sent:
            logger.info(f"OTP successfully sent to {email}")
        else:
            logger.warning(f"OTP generated but not sent (Mailgun not configured) - OTP: {otp_code}")

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

