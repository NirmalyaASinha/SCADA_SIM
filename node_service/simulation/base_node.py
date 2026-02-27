"""
Base Node Simulation Class
Provides common functionality for all SCADA node types
"""

import asyncio
import logging
import math
import random
from datetime import datetime, time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class AlarmConfig:
    """Alarm threshold configuration"""
    tag: str
    priority: int  # 1=CRITICAL, 2=HIGH, 3=MEDIUM, 4=LOW, 5=INFO
    high_limit: Optional[float] = None
    low_limit: Optional[float] = None
    message_template: str = "{tag} out of range: {value}"


@dataclass
class NodeState:
    """Current state of a SCADA node"""
    node_id: str
    node_type: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Common electrical parameters
    bus_voltage_kv: float = 0.0
    line_current_a: float = 0.0
    active_power_mw: float = 0.0
    reactive_power_mvar: float = 0.0
    power_factor: float = 0.0
    frequency_hz: float = 50.0
    
    # Equipment parameters (node-type specific)
    transformer_temp_c: Optional[float] = None
    tap_position: Optional[int] = None
    generator_rpm: Optional[int] = None
    load_percentage: Optional[float] = None
    
    # Digital/Boolean states
    breaker_state: bool = True  # True=closed, False=open
    relay_trip: bool = False
    earth_fault: bool = False
    outage_flag: bool = False
    feeder_switch: bool = True
    
    # Operational state
    node_state: str = "NORMAL"  # NORMAL, WARNING, FAULT, ISOLATED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}


class BaseNode:
    """
    Base class for all SCADA node simulations
    Implements realistic electrical behavior with:
    - 24-hour load profile (Indian grid pattern)
    - Gaussian noise on all measurements
    - Thermal lag simulation
    - System-wide frequency coupling
    - Protection relay logic
    """
    
    def __init__(self, node_id: str, node_type: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config
        
        # Current state
        self.state = NodeState(node_id=node_id, node_type=node_type)
        
        # Shared frequency (system-wide)
        self._system_frequency = 50.0
        
        # Nominal operating points (to be set by subclasses)
        self.nominal_values = {}
        self.operating_ranges = {}
        
        # Alarm configuration
        self.alarm_configs: List[AlarmConfig] = []
        self.active_alarms: Dict[str, Dict] = {}
        
        # Simulation parameters
        self.simulation_step = 1.0  # seconds
        self.noise_std = 0.003  # 0.3% standard deviation
        
        # Operational state management (new)
        self._isolation_flag = False  # True when node is isolated
        self._standby_flag = False  # True when node is on standby
        self._applied_voltage = None  # Manually set voltage (overrides simulation)
        
        # For thermal lag simulation
        self._thermal_time_constant = 300.0  # 5 minutes in seconds
        self._previous_temp = None
        
        # Running flag
        self._running = False
        self._simulation_task: Optional[asyncio.Task] = None
        
        logger.info(f"Initialized {node_type} node: {node_id}")
    
    def set_system_frequency(self, frequency: float):
        """Set system-wide frequency (called from master or shared state)"""
        self._system_frequency = frequency
        self.state.frequency_hz = frequency
    
    def get_load_factor(self) -> float:
        """
        Calculate load factor based on time of day
        Simulates Indian grid load profile:
        - Peak 1: 10:00 (morning peak) = 0.95
        - Peak 2: 20:00 (evening peak) = 1.00
        - Trough: 03:00 (night minimum) = 0.40
        
        Returns: load factor (0.0 to 1.0)
        """
        now = datetime.now()
        hour = now.hour + now.minute / 60.0
        
        # Sinusoidal approximation with two peaks
        # Base sine wave for daily cycle
        base = 0.65 + 0.25 * math.sin(2 * math.pi * (hour - 3) / 24)
        
        # Morning peak boost (10:00)
        morning_boost = 0.15 * math.exp(-((hour - 10) ** 2) / 8)
        
        # Evening peak boost (20:00)
        evening_boost = 0.20 * math.exp(-((hour - 20) ** 2) / 8)
        
        load_factor = base + morning_boost + evening_boost
        
        # Clamp to valid range
        return max(0.4, min(1.0, load_factor))
    
    def add_noise(self, value: float, nominal: float) -> float:
        """
        Add Gaussian noise to a measurement
        
        Args:
            value: Current value
            nominal: Nominal value for scaling noise
        
        Returns: Value with noise added
        """
        noise = random.gauss(0, self.noise_std * nominal)
        return value + noise
    
    def simulate_thermal_lag(self, target_temp: float, current_temp: Optional[float]) -> float:
        """
        Simulate thermal lag using first-order exponential model
        
        Args:
            target_temp: Target temperature based on load
            current_temp: Current temperature (None on first call)
        
        Returns: Temperature with thermal lag applied
        """
        if current_temp is None:
            return target_temp
        
        # First-order lag: T(t+dt) = T(t) + (T_target - T(t)) * dt / tau
        alpha = self.simulation_step / self._thermal_time_constant
        return current_temp + alpha * (target_temp - current_temp)
    
    def check_alarms(self):
        """
        Check all alarm conditions and raise/clear alarms
        """
        state_dict = self.state.to_dict()
        
        for alarm_config in self.alarm_configs:
            tag = alarm_config.tag
            if tag not in state_dict:
                continue
            
            value = state_dict[tag]
            alarm_key = f"{self.node_id}_{tag}"
            
            # Check if alarm should be raised
            is_alarm = False
            if alarm_config.high_limit is not None and value > alarm_config.high_limit:
                is_alarm = True
            if alarm_config.low_limit is not None and value < alarm_config.low_limit:
                is_alarm = True
            
            if is_alarm and alarm_key not in self.active_alarms:
                # Raise new alarm
                self.active_alarms[alarm_key] = {
                    'alarm_id': alarm_key,
                    'node_id': self.node_id,
                    'tag': tag,
                    'priority': alarm_config.priority,
                    'value': value,
                    'message': alarm_config.message_template.format(tag=tag, value=value),
                    'raised_time': datetime.utcnow().isoformat()
                }
                logger.warning(f"Alarm raised: {alarm_key} = {value}")
            
            elif not is_alarm and alarm_key in self.active_alarms:
                # Clear alarm
                logger.info(f"Alarm cleared: {alarm_key}")
                del self.active_alarms[alarm_key]
    
    def update_operational_state(self):
        """
        Update overall node operational state based on conditions
        """
        if self.active_alarms:
            # Check for critical alarms
            critical_alarms = [a for a in self.active_alarms.values() if a['priority'] == 1]
            if critical_alarms:
                self.state.node_state = "FAULT"
                return
            
            # Check for high priority alarms
            high_alarms = [a for a in self.active_alarms.values() if a['priority'] == 2]
            if high_alarms:
                self.state.node_state = "WARNING"
                return
        
        # Check digital fault states
        if self.state.relay_trip or self.state.earth_fault:
            self.state.node_state = "FAULT"
            return
        
        # Breaker open but no fault
        if not self.state.breaker_state:
            self.state.node_state = "ISOLATED"
            return
        
        # All normal
        self.state.node_state = "NORMAL"
    
    # =========================================================================
    # STATE CONTROL METHODS (called from API)
    # =========================================================================
    
    def set_isolation(self, isolated: bool):
        """Set or clear node isolation state"""
        self._isolation_flag = isolated
        if isolated:
            self.state.node_state = "ISOLATED"
            self.state.breaker_state = False
            self.state.active_power_mw = 0.0
            logger.info(f"Node {self.node_id} ISOLATED")
        else:
            logger.info(f"Node {self.node_id} isolation cleared")
    
    def is_isolated(self) -> bool:
        """Check if node is isolated"""
        return self._isolation_flag
    
    def set_standby(self, on_standby: bool):
        """Set or clear node standby state"""
        self._standby_flag = on_standby
        if on_standby:
            self.state.node_state = "STANDBY"
            self.state.active_power_mw = 0.0  # No power output when on standby
            logger.info(f"Node {self.node_id} on STANDBY")
        else:
            logger.info(f"Node {self.node_id} returning to NORMAL")
    
    def is_standby(self) -> bool:
        """Check if node is on standby"""
        return self._standby_flag
    
    def get_operational_state(self) -> str:
        """Get the operational state as a string (ISOLATED, STANDBY, or ONLINE)"""
        if self._isolation_flag:
            return "ISOLATED"
        elif self._standby_flag:
            return "STANDBY"
        else:
            return "ONLINE"
    
    def set_applied_voltage(self, voltage_kv: float):
        """Set voltage to be applied (overrides simulation)"""
        self._applied_voltage = voltage_kv
        logger.info(f"Node {self.node_id} voltage set to {voltage_kv} kV")
    
    def get_applied_voltage(self) -> Optional[float]:
        """Get the manually applied voltage"""
        return self._applied_voltage
    
    def clear_applied_voltage(self):
        """Clear manually applied voltage (use simulation default)"""
        self._applied_voltage = None
    
    def enforce_state_constraints(self):
        """
        Enforce operational state constraints
        Called at each simulation step to enforce:
        - Isolation: breaker off, no power, low voltage
        - Standby: reduced power, normal voltage
        """
        if self._isolation_flag:
            self.state.breaker_state = False
            self.state.active_power_mw = 0.0
            self.state.line_current_a = 0.0
            if self._applied_voltage is None:
                self.state.bus_voltage_kv = 0.0
        
        if self._standby_flag:
            self.state.active_power_mw = 0.0
            self.state.line_current_a = max(0.0, self.state.line_current_a * 0.05)  # Minimal standby current
    
    def apply_voltage_override(self):
        """Apply manually set voltage if defined"""
        if self._applied_voltage is not None and not self._isolation_flag:
            self.state.bus_voltage_kv = self._applied_voltage
    
    def simulate_frequency(self) -> float:
        """
        Simulate system frequency with realistic variation
        
        System frequency is shared across all nodes but has small variations
        based on load-generation balance
        """
        # Base frequency from system
        base_freq = self._system_frequency
        
        # Add small random walk
        variation = random.gauss(0, 0.015)  # ±0.015 Hz std dev
        
        # Clamp to realistic limits
        freq = max(49.5, min(50.5, base_freq + variation))
        
        # Update system frequency (slight drift)
        self._system_frequency = 0.99 * self._system_frequency + 0.01 * freq
        
        return freq
    
    async def simulation_loop(self):
        """
        Main simulation loop - runs continuously
        Override in subclasses to implement specific behavior
        """
        logger.info(f"Starting simulation loop for {self.node_id}")
        
        while self._running:
            try:
                # Update timestamp
                self.state.timestamp = datetime.utcnow().isoformat()
                
                # Simulate frequency
                self.state.frequency_hz = self.simulate_frequency()
                
                # Call subclass update method
                await self.update_simulation()
                
                # Enforce state constraints (isolation, standby)
                self.enforce_state_constraints()
                
                # Apply voltage override if set
                self.apply_voltage_override()
                
                # Check alarms
                self.check_alarms()
                
                # Update operational state
                self.update_operational_state()
                
                # Wait for next simulation step
                await asyncio.sleep(self.simulation_step)
                
            except Exception as e:
                logger.error(f"Error in simulation loop for {self.node_id}: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def update_simulation(self):
        """
        Update simulation state - MUST be overridden by subclasses
        """
        raise NotImplementedError("Subclasses must implement update_simulation()")
    
    async def start(self):
        """Start the simulation"""
        if self._running:
            logger.warning(f"Simulation already running for {self.node_id}")
            return
        
        self._running = True
        self._simulation_task = asyncio.create_task(self.simulation_loop())
        logger.info(f"Simulation started for {self.node_id}")
    
    async def stop(self):
        """Stop the simulation"""
        if not self._running:
            return
        
        self._running = False
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Simulation stopped for {self.node_id}")
    
    def get_state(self) -> NodeState:
        """Get current node state"""
        return self.state
    
    def get_alarms(self) -> List[Dict]:
        """Get all active alarms"""
        return list(self.active_alarms.values())
    
    # Control methods (called by operators or admin)
    
    def set_breaker(self, state: bool, reason: str = "Operator command") -> Dict[str, Any]:
        """
        Open or close the main breaker
        
        Args:
            state: True=close, False=open
            reason: Reason for the action
        
        Returns: Result dict
        """
        old_state = self.state.breaker_state
        self.state.breaker_state = state
        
        action = "CLOSED" if state else "OPENED"
        logger.info(f"{self.node_id} breaker {action}: {reason}")
        
        return {
            'success': True,
            'action': f'breaker_{action.lower()}',
            'old_state': old_state,
            'new_state': state,
            'reason': reason
        }
    
    def set_tap_position(self, position: int, reason: str = "Operator command") -> Dict[str, Any]:
        """
        Set transformer tap changer position (substations only)
        
        Args:
            position: Tap position (1-17)
            reason: Reason for the action
        
        Returns: Result dict
        """
        if self.state.tap_position is None:
            return {
                'success': False,
                'error': 'Node does not have tap changer'
            }
        
        if not (1 <= position <= 17):
            return {
                'success': False,
                'error': 'Tap position must be between 1 and 17'
            }
        
        old_position = self.state.tap_position
        self.state.tap_position = position
        
        logger.info(f"{self.node_id} tap changed {old_position} -> {position}: {reason}")
        
        return {
            'success': True,
            'action': 'tap_position_set',
            'old_position': old_position,
            'new_position': position,
            'reason': reason
        }
