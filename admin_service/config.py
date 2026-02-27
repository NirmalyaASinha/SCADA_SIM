"""
Admin Service Configuration
Loads configuration from environment variables
"""

import os


class AdminConfig:
    """Admin service configuration"""
    
    def __init__(self):
        # Server ports
        self.API_PORT = int(os.getenv('API_PORT', '9000'))
        self.DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '3000'))
        
        # Database configuration
        self.DB_URL = os.getenv(
            'DB_URL',
            'postgresql://scada:scada123@localhost:5432/scadadb'
        )
        
        # Redis configuration
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # JWT secret for admin authentication
        self.JWT_SECRET = os.getenv('JWT_SECRET', 'scada-admin-secret-change-in-prod')

        # Shared token for admin -> node service control calls
        self.MASTER_API_TOKEN = os.getenv('MASTER_API_TOKEN', 'scada-master-token')
        
        # Admin credentials (default, should be changed in production)
        self.ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
        self.ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin@scada2024')
    
    def __repr__(self):
        return (
            f"AdminConfig(\n"
            f"  API_PORT={self.API_PORT},\n"
            f"  DASHBOARD_PORT={self.DASHBOARD_PORT},\n"
            f"  DB_URL={'***'},\n"
            f"  REDIS_URL={self.REDIS_URL}\n"
            f")"
        )
