"""
Admin Service API Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    error: Optional[str] = None


class NodeRegistration(BaseModel):
    node_id: str
    node_type: str
    ip: str
    rest_port: int
    modbus_port: int
    ws_port: int
    version: str = "1.0.0"


class HeartbeatRequest(BaseModel):
    timestamp: str
    status: str


class GridOverview(BaseModel):
    total_generation_mw: float
    total_load_mw: float
    grid_frequency_hz: float
    grid_losses_mw: float
    loss_percentage: float
    nodes_online: int
    nodes_total: int
    timestamp: str


class NodeDetail(BaseModel):
    node_id: str
    node_type: str
    ip: str
    rest_port: int
    modbus_port: int
    ws_port: int
    status: str
    last_heartbeat: str
    registered_at: str


class ControlRequest(BaseModel):
    action: str
    reason: str
    value: Optional[Any] = None


class IsolateRequest(BaseModel):
    reason: str = "Emergency Isolation"
    force: bool = False
