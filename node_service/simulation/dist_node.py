"""
Distribution Node Simulation
Simulates distribution substations and feeders
"""

import logging
import random
from typing import Dict, Any

from .base_node import BaseNode, AlarmConfig

logger = logging.getLogger(__name__)


class DistributionNode(BaseNode):
    """
    Distribution node simulation
    
    Parameters simulated:
    - bus_voltage_kv: 0.415-11 kV (nominal 11 kV)
    - line_current_a: 50-400 A (nominal 200 A)
    - active_power_mw: 1-50 MW (nominal 25 MW)
    - load_percentage: 20-95% (nominal 60%)
    - power_factor: 0.75-0.95 (nominal 0.88)
    - breaker_state, feeder_switch, outage_flag
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        super().__init__(node_id, "distribution", config)
        
        # Nominal operating points
        self.nominal_values = {
            'bus_voltage_kv': 11.0,
            'line_current_a': 200.0,
            'active_power_mw': 25.0,
            'load_percentage': 60.0,
            'power_factor': 0.88,
        }
        
        # Operating ranges
        self.operating_ranges = {
            'bus_voltage_kv': (0.415, 11.0),
            'line_current_a': (50.0, 400.0),
            'active_power_mw': (1.0, 50.0),
            'load_percentage': (20.0, 95.0),
            'power_factor': (0.75, 0.95),
        }
        
        # Set initial state
        self.state.bus_voltage_kv = self.nominal_values['bus_voltage_kv']
        self.state.line_current_a = self.nominal_values['line_current_a']
        self.state.active_power_mw = self.nominal_values['active_power_mw']
        self.state.load_percentage = self.nominal_values['load_percentage']
        self.state.power_factor = self.nominal_values['power_factor']
        self.state.breaker_state = True
        self.state.feeder_switch = True
        self.state.outage_flag = False
        
        # Reactive power (calculated from active power and power factor)
        self.state.reactive_power_mvar = self._calculate_reactive_power(
            self.state.active_power_mw,
            self.state.power_factor
        )
        
        # Configure alarms
        self.alarm_configs = [
            AlarmConfig(
                tag='bus_voltage_kv',
                priority=2,
                high_limit=11.5,
                low_limit=10.0,
                message_template="Bus voltage {value:.2f} kV out of limits"
            ),
            AlarmConfig(
                tag='line_current_a',
                priority=2,
                high_limit=380.0,
                low_limit=None,
                message_template="Line current {value:.1f} A exceeds limit"
            ),
            AlarmConfig(
                tag='load_percentage',
                priority=3,
                high_limit=90.0,
                low_limit=None,
                message_template="Load {value:.1f}% approaching limit"
            ),
            AlarmConfig(
                tag='power_factor',
                priority=4,
                high_limit=None,
                low_limit=0.80,
                message_template="Power factor {value:.3f} below target"
            ),
        ]
        
        # Outage simulation (random rare events)
        self._outage_probability = 0.0002  # 0.02% per simulation step
        self._outage_duration = 0  # seconds remaining in outage
        
        logger.info(f"DistributionNode {node_id} initialized")
    
    def _calculate_reactive_power(self, active_mw: float, pf: float) -> float:
        """Calculate reactive power from active power and power factor"""
        if pf >= 1.0 or pf <= 0:
            return 0.0
        
        # Q = P * tan(arccos(pf))
        import math
        angle = math.acos(pf)
        reactive_mvar = active_mw * math.tan(angle)
        return reactive_mvar
    
    async def update_simulation(self):
        """Update distribution node simulation"""
        
        # Get load factor (time of day)
        load_factor = self.get_load_factor()
        
        # Handle ongoing outage
        if self._outage_duration > 0:
            self._outage_duration -= self.simulation_step
            if self._outage_duration <= 0:
                self.state.outage_flag = False
                logger.info(f"{self.node_id} outage cleared")
        
        # If breaker/feeder is open or outage, reduce power to zero
        if (not self.state.breaker_state or 
            not self.state.feeder_switch or 
            self.state.outage_flag):
            target_power = 0.0
            target_current = 0.0
            target_load_pct = 0.0
        else:
            # Normal operation - follows load curve
            # Load percentage varies with time of day
            target_load_pct = self.nominal_values['load_percentage'] * load_factor
            
            # Power is proportional to load percentage
            max_power = self.operating_ranges['active_power_mw'][1]
            target_power = max_power * (target_load_pct / 100.0)
            
            # Power factor varies slightly with load (lower at light loads)
            if load_factor < 0.5:
                target_pf = 0.82
            elif load_factor < 0.75:
                target_pf = 0.86
            else:
                target_pf = self.nominal_values['power_factor']
            
            # Calculate current from power
            # P = sqrt(3) * V * I * pf
            voltage = self.nominal_values['bus_voltage_kv']
            target_current = (target_power * 1000) / (1.732 * voltage * target_pf)
        
        # Update voltage with noise (distribution voltage is less stable)
        voltage_noise = random.gauss(0, 0.15)  # More variation at distribution level
        self.state.bus_voltage_kv = self.nominal_values['bus_voltage_kv'] + voltage_noise
        
        # Clamp to operating range
        self.state.bus_voltage_kv = max(
            self.operating_ranges['bus_voltage_kv'][0],
            min(self.operating_ranges['bus_voltage_kv'][1], self.state.bus_voltage_kv)
        )
        
        # Update power with noise
        self.state.active_power_mw = self.add_noise(
            target_power,
            self.nominal_values['active_power_mw']
        )
        
        # Update current with noise
        self.state.line_current_a = self.add_noise(
            target_current,
            self.nominal_values['line_current_a']
        )
        
        # Update load percentage
        max_power = self.operating_ranges['active_power_mw'][1]
        self.state.load_percentage = (self.state.active_power_mw / max_power) * 100.0
        
        if not self.state.breaker_state or not self.state.feeder_switch or self.state.outage_flag:
            self.state.load_percentage = 0.0
        
        # Update power factor with noise
        if target_power > 0:
            target_pf = 0.88 if load_factor > 0.5 else 0.82
            self.state.power_factor = max(0.75, min(0.95, 
                target_pf + random.gauss(0, 0.01)
            ))
        else:
            self.state.power_factor = 0.0
        
        # Calculate reactive power
        self.state.reactive_power_mvar = self._calculate_reactive_power(
            self.state.active_power_mw,
            self.state.power_factor if self.state.power_factor > 0 else 0.88
        )
        
        # Simulate random outages (very rare)
        if (not self.state.outage_flag and 
            self.state.breaker_state and 
            self.state.feeder_switch and
            random.random() < self._outage_probability):
            self.state.outage_flag = True
            # Outage lasts 30-180 seconds
            self._outage_duration = random.uniform(30, 180)
            logger.error(f"{self.node_id} OUTAGE! Duration: {self._outage_duration:.0f}s")
        
        # Over-current protection (circuit breaker trips)
        if self.state.line_current_a > 390.0 and self.state.breaker_state:
            self.state.breaker_state = False
            logger.error(f"{self.node_id} breaker tripped: over-current {self.state.line_current_a:.1f} A")
        
        # Apply operational state constraints (isolation, standby, voltage override)
        self.enforce_state_constraints()
        self.apply_voltage_override()
    
    def set_feeder_switch(self, state: bool, reason: str = "Operator command") -> Dict[str, Any]:
        """
        Open or close the feeder switch
        
        Args:
            state: True=close, False=open
            reason: Reason for the action
        
        Returns: Result dict
        """
        old_state = self.state.feeder_switch
        self.state.feeder_switch = state
        
        action = "CLOSED" if state else "OPENED"
        logger.info(f"{self.node_id} feeder switch {action}: {reason}")
        
        return {
            'success': True,
            'action': f'feeder_{action.lower()}',
            'old_state': old_state,
            'new_state': state,
            'reason': reason
        }
    
    def acknowledge_outage(self) -> Dict[str, Any]:
        """Acknowledge and clear outage flag (after repair)"""
        if not self.state.outage_flag:
            return {'success': False, 'error': 'No active outage'}
        
        self.state.outage_flag = False
        self._outage_duration = 0
        logger.info(f"{self.node_id} outage acknowledged and cleared")
        
        return {'success': True, 'action': 'outage_cleared'}
