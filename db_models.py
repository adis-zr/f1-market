from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum
from passlib.context import CryptContext

db = SQLAlchemy()
otp_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserRole(enum.Enum):
    PLAYER = "player"
    ADMIN = "admin"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True, index=True)
    role = db.Column(db.String(20), nullable=False, default=UserRole.PLAYER.value, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
    
    # Role helpers
    def is_admin(self):
        return self.role == UserRole.ADMIN.value
    
    def is_player(self):
        return self.role == UserRole.PLAYER.value

class OTP(db.Model):
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<OTP {self.email}>'
    
    def set_code(self, code: str):
        """Hash and store the OTP code."""
        self.code_hash = otp_context.hash(code)
    
    def verify_code(self, code: str) -> bool:
        """Verify an OTP code against the stored hash."""
        return otp_context.verify(code, self.code_hash)
    
    def is_valid(self):
        """Check if OTP is still valid (not expired and not used)."""
        return not self.used and datetime.utcnow() < self.expires_at

