# utils/tokens.py
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import hashlib

def generate_reset_token(email):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, max_age=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=max_age)
    except Exception:
        return None
    return email

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def check_token_hash(token, token_hash):
    return hashlib.sha256(token.encode()).hexdigest() == token_hash
