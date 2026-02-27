"""
Admin Service REST API
"""

from .routes import create_admin_app
from .auth import AdminAuthHandler

__all__ = ['create_admin_app', 'AdminAuthHandler']
