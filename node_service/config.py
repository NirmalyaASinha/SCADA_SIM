"""
Node Service Configuration
Loads configuration from environment variables
"""

import os
import socket
from typing import Optional


def get_local_ip() -> str:
    """Get local IP address"""
    try:
        # Create a socket and connect to an external address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class NodeConfig:
    """Node service configuration"""
    
    def __init__(self, master_ip: Optional[str] = None, master_port: Optional[int] = None):
        # Node identification
        self.NODE_ID = os.getenv('NODE_ID', 'GEN-001')
        self.NODE_TYPE = os.getenv('NODE_TYPE', 'generation')
        self.UNIT_ID = int(os.getenv('UNIT_ID', '1'))
        
        # Network configuration
        self.MY_IP = os.getenv('MY_IP', get_local_ip())
        self.REST_PORT = int(os.getenv('REST_PORT', '8101'))
        self.WS_PORT = int(os.getenv('WS_PORT', '8102'))
        self.MODBUS_PORT = int(os.getenv('MODBUS_PORT', '5020'))
        
        # Master configuration (from startup dialog or env)
        if master_ip and master_port:
            self.MASTER_IP = master_ip
            self.MASTER_PORT = master_port
        else:
            self.MASTER_IP = os.getenv('MASTER_IP', 'localhost')
            self.MASTER_PORT = int(os.getenv('MASTER_PORT', '9000'))
        
        # Auto-connect mode (skip dialog in Docker)
        self.AUTO_CONNECT = os.getenv('AUTO_CONNECT', 'false').lower() == 'true'
        
        # Database configuration
        self.DB_URL = os.getenv(
            'DB_URL',
            'postgresql://scada:scada123@localhost:5432/scadadb'
        )
        
        # Operator credentials (optional, uses defaults if not set)
        self.OPERATOR_USERNAME = os.getenv('OPERATOR_USERNAME')
        self.OPERATOR_PASSWORD = os.getenv('OPERATOR_PASSWORD')
        
        # JWT secret
        self.JWT_SECRET = os.getenv('JWT_SECRET', 'node-secret-change-in-production')
    
    def __repr__(self):
        return (
            f"NodeConfig(\n"
            f"  NODE_ID={self.NODE_ID},\n"
            f"  NODE_TYPE={self.NODE_TYPE},\n"
            f"  MY_IP={self.MY_IP},\n"
            f"  REST_PORT={self.REST_PORT},\n"
            f"  WS_PORT={self.WS_PORT},\n"
            f"  MODBUS_PORT={self.MODBUS_PORT},\n"
            f"  MASTER={self.MASTER_IP}:{self.MASTER_PORT}\n"
            f")"
        )
