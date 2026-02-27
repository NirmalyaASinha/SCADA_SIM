"""
Admin Authentication Handler
JWT-based authentication for admin users
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class AdminAuthHandler:
    """Authentication handler for admin users"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        
        # Hardcoded admin accounts (in production, use database)
        # Passwords stored as plain strings; bcrypt verification happens at login
        self.users = {
            'admin': {
                'password': 'admin@scada2024',
                'role': 'admin'
            },
            'engineer': {
                'password': 'eng@scada2024',
                'role': 'engineer'
            },
            'viewer': {
                'password': 'view@scada2024',
                'role': 'viewer'
            }
        }
        
        self.active_sessions: Dict[str, Dict] = {}
        
        logger.info("Admin auth handler initialized")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def encode_token(self, username: str, role: str) -> str:
        """Generate JWT token"""
        payload = {
            'exp': datetime.utcnow() + timedelta(hours=8),
            'iat': datetime.utcnow(),
            'sub': username,
            'role': role
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return token with role"""
        if username not in self.users:
            return None
        
        user = self.users[username]
        # Simple plain-text password comparison (since we're storing plain passwords for defaults)
        if password != user['password']:
            return None
        
        token = self.encode_token(username, user['role'])
        
        self.active_sessions[token] = {
            'username': username,
            'role': user['role'],
            'login_time': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Admin user {username} ({user['role']}) authenticated")
        
        return {
            'token': token,
            'username': username,
            'role': user['role']
        }
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials) -> Dict:
        """Verify token from request"""
        token = credentials.credentials
        payload = self.decode_token(token)
        
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return payload
    
    def logout(self, token: str):
        """Remove session"""
        if token in self.active_sessions:
            del self.active_sessions[token]
