"""Shared authentication helpers for route handlers."""
from functools import wraps
from flask import session, jsonify
from db import db, User


def get_current_user_id():
    """Get current user ID from session.

    Returns:
        User ID if authenticated, None otherwise.
    """
    return session.get('user_id')


def get_current_user():
    """Get current user from session.

    Returns:
        User instance if authenticated, None otherwise.
    """
    user_id = get_current_user_id()
    if not user_id:
        return None
    return db.session.get(User, user_id)


def is_admin():
    """Check if current user is admin.

    Returns:
        True if current user is admin, False otherwise.
    """
    user = get_current_user()
    if not user:
        return False
    return user.is_admin()


def require_auth(f):
    """Decorator to require authentication for a route.

    Returns 401 if user is not authenticated.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user_id():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator to require admin role for a route.

    Returns 401 if not authenticated, 403 if not admin.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user_id():
            return jsonify({'error': 'Authentication required'}), 401
        if not is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated
