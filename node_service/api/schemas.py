"""
Pydantic schemas for Node Service API
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Authentication schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    operator: Optional[str] = None
    node_id: Optional[str] = None
    error: Optional[str] = None


# Node info schemas
class NodeInfo(BaseModel):
    node_id: str
    node_type: str
    version: str = "1.0.0"
    status: str
    uptime_seconds: float


class HealthResponse(BaseModel):
    status: str
    node_id: str
    timestamp: str
    services: Dict[str, str]


# Telemetry schemas
class TelemetryData(BaseModel):
    timestamp: str
    node_id: str
    node_type: str
    bus_voltage_kv: Optional[float] = None
    line_current_a: Optional[float] = None
    active_power_mw: Optional[float] = None
    reactive_power_mvar: Optional[float] = None
    power_factor: Optional[float] = None
    frequency_hz: Optional[float] = None
    transformer_temp_c: Optional[float] = None
    tap_position: Optional[int] = None
    load_percentage: Optional[float] = None
    generator_rpm: Optional[int] = None
    breaker_state: Optional[bool] = None
    relay_trip: Optional[bool] = None
    earth_fault: Optional[bool] = None
    outage_flag: Optional[bool] = None
    feeder_switch: Optional[bool] = None
    node_state: str


# Control schemas
class BreakerControlRequest(BaseModel):
    action: str = Field(..., pattern="^(open|close)$")
    reason: str


class BreakerControlResponse(BaseModel):
    success: bool
    action: str
    old_state: Optional[bool] = None
    new_state: Optional[bool] = None
    reason: str
    error: Optional[str] = None


class TapControlRequest(BaseModel):
    position: int = Field(..., ge=1, le=17)
    reason: str


class TapControlResponse(BaseModel):
    success: bool
    action: Optional[str] = None
    old_position: Optional[int] = None
    new_position: Optional[int] = None
    reason: str
    error: Optional[str] = None


class SetpointRequest(BaseModel):
    tag: str
    value: float
    reason: str


class SetpointResponse(BaseModel):
    success: bool
    action: Optional[str] = None
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    tag: str
    reason: str
    error: Optional[str] = None


# Alarm schemas
class Alarm(BaseModel):
    alarm_id: str
    node_id: str
    tag: str
    priority: int
    message: str
    value: Optional[float] = None
    raised_time: str


class AlarmListResponse(BaseModel):
    alarms: List[Alarm]
    total: int


# Event schemas
class Event(BaseModel):
    timestamp: str
    event_type: str
    operator: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


class EventListResponse(BaseModel):
    events: List[Event]
    total: int


# Connection schemas
class Connection(BaseModel):
    protocol: str
    client_ip: str
    client_port: Optional[int] = None
    connected_at: str
    request_count: int
    is_authenticated: bool
    username: Optional[str] = None


class ConnectionListResponse(BaseModel):
    connections: List[Connection]
    total: int


# Modbus info schema
class ModbusRegisterInfo(BaseModel):
    address: int
    name: str
    unit: str
    scale_factor: float
    writable: bool
    description: str


class ModbusCoilInfo(BaseModel):
    address: int
    name: str
    writable: bool
    description: str


class ModbusInfo(BaseModel):
    node_id: str
    unit_id: int
    port: int
    protocol: str
    authentication: bool
    encryption: bool
    registers: List[ModbusRegisterInfo]
    coils: List[ModbusCoilInfo]
    status: str


# Audit log schema
class AuditEntry(BaseModel):
    timestamp: str
    operator: str
    operator_ip: str
    action_type: str
    action_detail: Dict[str, Any]
    result: str


class AuditListResponse(BaseModel):
    entries: List[AuditEntry]
    total: int


# New control schemas for advanced features
class VoltageAdjustRequest(BaseModel):
    voltage_kv: float
    reason: str
    password: str = ""


class StandbyRequest(BaseModel):
    reason: str
    duration_minutes: int = 60


class IsolateRequest(BaseModel):
    reason: str = "Emergency Isolation"
    force: bool = False

class StartNodeRequest(BaseModel):
    reason: str = "Restoring from standby"


class DeenergizeRequest(BaseModel):
    reason: str = "Upstream power loss"


class ReenergizeRequest(BaseModel):
    reason: str = "Upstream power restored"