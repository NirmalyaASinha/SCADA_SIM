"""
Authentication handler for Node Service API
Simple JWT-based authentication for operators
"""

import os
import time
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()


class AuthHandler:
    """
    Authentication handler for node operators
    
    Each node has its own operator credentials (configurable via env vars)
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.secret_key = os.getenv('JWT_SECRET', 'node-secret-change-in-production')
        self.master_token = os.getenv('MASTER_API_TOKEN', '')
        
        # Load operator credentials from environment
        # Format: OPERATOR_USERNAME and OPERATOR_PASSWORD
        self.operator_username = os.getenv('OPERATOR_USERNAME', self._default_username())
        self.operator_password = os.getenv('OPERATOR_PASSWORD', self._default_password())
        
        # Store plain password (avoid bcrypt initialization issues)
        # In production, use proper password hashing
        self.operator_password_plain = self.operator_password
        
        # Active sessions
        self.active_sessions: Dict[str, Dict] = {}
        
        logger.info(f"Auth handler initialized for {node_id}")
        logger.info(f"Default operator: {self.operator_username}")
    
    def _default_username(self) -> str:
        """Generate default username based on node ID"""
        # GEN-001 -> operator_gen001
        # SUB-001 -> operator_sub001
        # DIST-001 -> operator_dist001
        node_type = self.node_id.split('-')[0].lower()
        node_num = self.node_id.split('-')[1]
        return f"operator_{node_type}{node_num}"
    
    def _default_password(self) -> str:
        """Generate default password based on node ID"""
        # GEN-001 -> gen001@scada
        # SUB-001 -> sub001@scada
        node_type = self.node_id.split('-')[0].lower()
        node_num = self.node_id.split('-')[1]
        return f"{node_type}{node_num}@scada"
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def encode_token(self, username: str) -> str:
        """
        Generate JWT token
        
        Args:
            username: Operator username
        
        Returns: JWT token string
        """
        payload = {
            'exp': datetime.utcnow() + timedelta(hours=8),  # 8 hour expiration
            'iat': datetime.utcnow(),
            'sub': username,
            'node_id': self.node_id
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """
        Decode and verify JWT token
        
        Args:
            token: JWT token string
        
        Returns: Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user and return token
        
        Args:
            username: Username
            password: Plain text password
        
        Returns: JWT token if successful, None otherwise
        """
        # Check username
        if username != self.operator_username:
            logger.warning(f"Authentication failed: unknown user {username}")
            return None
        
        # Verify password (simple plain-text comparison)
        if password != self.operator_password_plain:
            logger.warning(f"Authentication failed: invalid password for {username}")
            return None
        
        # Generate token
        token = self.encode_token(username)
        
        # Store session
        self.active_sessions[token] = {
            'username': username,
            'login_time': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }
        
        logger.info(f"User {username} authenticated successfully")
        return token
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials) -> str:
        """
        Verify token from request
        
        Args:
            credentials: HTTP authorization credentials
        
        Returns: Username if valid
        
        Raises:
            HTTPException: If token is invalid
        """
        token = credentials.credentials
        if self.master_token and token == self.master_token:
            return 'master'
        payload = self.decode_token(token)
        
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Update last activity
        if token in self.active_sessions:
            self.active_sessions[token]['last_activity'] = datetime.utcnow().isoformat()
        
        return payload['sub']
    
    def logout(self, token: str):
        """Remove session"""
        if token in self.active_sessions:
            username = self.active_sessions[token]['username']
            del self.active_sessions[token]
            logger.info(f"User {username} logged out")
    
    def get_active_sessions(self) -> list:
        """Get list of active sessions"""
        return [
            {
                'username': session['username'],
                'login_time': session['login_time'],
                'last_activity': session['last_activity']
            }
            for session in self.active_sessions.values()
        ]
