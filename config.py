"""Application configuration."""
import os
import secrets
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file (for local dev)
load_dotenv()


def create_app_config(app: Flask) -> None:
    """Configure Flask application with all settings."""
    # Environment
    env = os.environ.get('FLASK_ENV', 'development').lower()

    # Session configuration
    secret_key = os.environ.get('SECRET_KEY')
    if env == 'production':
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be set in production")
        app.config['SECRET_KEY'] = secret_key
    else:
        # In dev, generate one if not provided
        app.config['SECRET_KEY'] = secret_key or secrets.token_hex(32)

    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Database configuration
    if env == 'production':
        # In production, prefer INTERNAL_PROD_DATABASE_URL
        database_url = os.environ.get('INTERNAL_PROD_DATABASE_URL')
        if not database_url:
            raise RuntimeError("INTERNAL_PROD_DATABASE_URL or DATABASE_URL must be set in production")
        # Ensure we use psycopg (v3) driver instead of psycopg2
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "app.db")}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Mailgun configuration
    app.config['MAILGUN_API_KEY'] = os.environ.get('MAILGUN_API_KEY')
    app.config['MAILGUN_DOMAIN'] = os.environ.get('MAILGUN_DOMAIN')

    # Default from email: if MAILGUN_DOMAIN is mg.gridstock.io, use noreply@gridstock.io
    mailgun_domain = os.environ.get('MAILGUN_DOMAIN', '')
    if mailgun_domain.startswith('mg.'):
        default_from = f'noreply@{mailgun_domain[3:]}'  # Remove 'mg.' prefix
    else:
        default_from = f'noreply@{mailgun_domain}' if mailgun_domain else 'noreply@example.com'
    app.config['MAILGUN_FROM_EMAIL'] = os.environ.get('MAILGUN_FROM_EMAIL', default_from)


def is_mailgun_configured(app: Flask) -> bool:
    """Check if Mailgun is properly configured."""
    return bool(app.config['MAILGUN_API_KEY'] and app.config['MAILGUN_DOMAIN'])

