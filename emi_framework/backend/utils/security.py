"""
Security Utilities
Password hashing, session management, and request authentication
"""

import os
import logging
import hashlib
import hmac
import secrets
import base64
from functools import wraps
from flask import session, jsonify, request

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD HASHING  (PBKDF2-HMAC-SHA256)
# ──────────────────────────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a random salt.
    Returns a single string:  <hex_salt>:<hex_hash>
    """
    salt   = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        plain_password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=260_000
    )
    return f"{salt}:{hashed.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash."""
    try:
        salt, expected_hash = stored_hash.split(':', 1)
        candidate = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=260_000
        )
        return hmac.compare_digest(candidate.hex(), expected_hash)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# SESSION-BASED AUTHENTICATION DECORATORS
# ──────────────────────────────────────────────────────────────────────────────

def login_required(f):
    """API decorator: requires a valid session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'customer_id' not in session:
            return jsonify({'error': 'Authentication required', 'code': 401}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """API decorator: requires admin-level session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'customer_id' not in session:
            return jsonify({'error': 'Authentication required', 'code': 401}), 401
        if not session.get('is_admin', False):
            return jsonify({'error': 'Admin access required', 'code': 403}), 403
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────────────
# CSRF TOKEN HELPER
# ──────────────────────────────────────────────────────────────────────────────

def generate_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session['csrf_token'] = token
    return token


def validate_csrf_token(token: str) -> bool:
    stored = session.get('csrf_token')
    if not stored:
        return False
    return hmac.compare_digest(stored, token)
