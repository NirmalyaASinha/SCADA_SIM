"""
Generation Node Simulation
Simulates power generation units (thermal/hydro/nuclear)
"""

import logging
import random
from typing import Dict, Any, Optional

from .base_node import BaseNode, AlarmConfig

logger = logging.getLogger(__name__)


class GenerationNode(BaseNode):
    """
    Generation node simulation
    
    Parameters simulated:
    - bus_voltage_kv: 220-400 kV (nominal 380 kV)
    - line_current_a: 500-2000 A (nominal 1200 A)
    - active_power_mw: 100-800 MW (nominal 500 MW)
    - reactive_power_mvar: 20-200 MVAR (nominal 80 MVAR)
    - frequency_hz: 49.5-50.5 Hz (nominal 50 Hz)
    - generator_rpm: 2940-3060 RPM (nominal 3000 RPM)
    - breaker_state, relay_trip
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        super().__init__(node_id, "generation", config)
        
        # Nominal operating points
        self.nominal_values = {
            'bus_voltage_kv': 380.0,
            'line_current_a': 1200.0,
            'active_power_mw': 500.0,
            'reactive_power_mvar': 80.0,
            'frequency_hz': 50.0,
            'generator_rpm': 3000,
        }
        
        # Operating ranges
        self.operating_ranges = {
            'bus_voltage_kv': (220.0, 400.0),
            'line_current_a': (500.0, 2000.0),
            'active_power_mw': (100.0, 800.0),
            'reactive_power_mvar': (20.0, 200.0),
            'frequency_hz': (49.5, 50.5),
            'generator_rpm': (2940, 3060),
        }
        
        # Set initial state
        self.state.bus_voltage_kv = self.nominal_values['bus_voltage_kv']
        self.state.line_current_a = self.nominal_values['line_current_a']
        self.state.active_power_mw = self.nominal_values['active_power_mw']
        self.state.reactive_power_mvar = self.nominal_values['reactive_power_mvar']
        self.state.frequency_hz = self.nominal_values['frequency_hz']
        self.state.generator_rpm = self.nominal_values['generator_rpm']
        self.state.breaker_state = True
        self.state.relay_trip = False
        
        # Configure alarms
        self.alarm_configs = [
            AlarmConfig(
                tag='bus_voltage_kv',
                priority=1,
                high_limit=395.0,
                low_limit=340.0,
                message_template="Bus voltage {value:.2f} kV out of limits"
            ),
            AlarmConfig(
                tag='line_current_a',
                priority=2,
                high_limit=1900.0,
                low_limit=None,
                message_template="Line current {value:.1f} A exceeds limit"
            ),
            AlarmConfig(
                tag='active_power_mw',
                priority=2,
                high_limit=780.0,
                low_limit=None,
                message_template="Active power {value:.1f} MW exceeds limit"
            ),
            AlarmConfig(
                tag='frequency_hz',
                priority=1,
                high_limit=50.3,
                low_limit=49.7,
                message_template="Frequency {value:.3f} Hz out of limits"
            ),
            AlarmConfig(
                tag='generator_rpm',
                priority=1,
                high_limit=3050,
                low_limit=2950,
                message_template="Generator speed {value} RPM out of limits"
            ),
        ]
        
        # Generation setpoint (can be controlled)
        self.power_setpoint_mw = self.nominal_values['active_power_mw']
        self.reactive_setpoint_mvar = self.nominal_values['reactive_power_mvar']
        
        logger.info(f"GenerationNode {node_id} initialized")
    
    async def update_simulation(self):
        """Update generation node simulation"""
        
        # Get load factor (time of day)
        load_factor = self.get_load_factor()
        
        # If breaker is open, reduce power to zero
        if not self.state.breaker_state:
            target_power = 0.0
            target_current = 0.0
            target_rpm = 2970  # Idling speed
        elif self.state.relay_trip:
            # Relay tripped - emergency shutdown
            target_power = 0.0
            target_current = 0.0
            target_rpm = 0
        else:
            # Normal operation - follow setpoint with load factor
            target_power = self.power_setpoint_mw * load_factor
            target_reactive = self.reactive_setpoint_mvar * load_factor
            
            # Calculate current from power
            # P = sqrt(3) * V * I * pf
            # I = P / (sqrt(3) * V * pf)
            pf = 0.95  # Typical power factor for generation
            voltage = self.state.bus_voltage_kv
            target_current = (target_power * 1000) / (1.732 * voltage * pf)
            
            # Generator RPM is tied to frequency
            # At 50 Hz, RPM = 3000 for 2-pole generator
            target_rpm = 3000 * (self.state.frequency_hz / 50.0)
        
        # Update voltage (relatively stable for generators)
        voltage_variation = random.gauss(0, 2.0)  # ±2 kV variation
        self.state.bus_voltage_kv = self.nominal_values['bus_voltage_kv'] + voltage_variation
        
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
        
        self.state.reactive_power_mvar = self.add_noise(
            target_reactive if not self.state.breaker_state else 0.0,
            self.nominal_values['reactive_power_mvar']
        )
        
        # Update current with noise
        self.state.line_current_a = self.add_noise(
            target_current,
            self.nominal_values['line_current_a']
        )
        
        # Update generator RPM
        self.state.generator_rpm = int(self.add_noise(
            target_rpm,
            self.nominal_values['generator_rpm']
        ))
        
        # Calculate power factor
        if self.state.active_power_mw > 0:
            apparent_power = (self.state.active_power_mw ** 2 + 
                            self.state.reactive_power_mvar ** 2) ** 0.5
            self.state.power_factor = self.state.active_power_mw / apparent_power
        else:
            self.state.power_factor = 0.0
        
        # Protection logic
        # Over-current protection
        if self.state.line_current_a > 1950:
            self.state.relay_trip = True
            logger.error(f"{self.node_id} relay tripped: over-current {self.state.line_current_a:.1f} A")
        
        # Over-frequency protection
        if self.state.frequency_hz > 50.4:
            self.state.relay_trip = True
            logger.error(f"{self.node_id} relay tripped: over-frequency {self.state.frequency_hz:.3f} Hz")
        
        # Under-frequency protection
        if self.state.frequency_hz < 49.6:
            self.state.relay_trip = True
            logger.error(f"{self.node_id} relay tripped: under-frequency {self.state.frequency_hz:.3f} Hz")
        
        # Apply operational state constraints (isolation, standby, voltage override)
        self.enforce_state_constraints()
        self.apply_voltage_override()
    
    def set_power_setpoint(self, active_mw: float, reactive_mvar: Optional[float] = None) -> Dict[str, Any]:
        """
        Set generator power setpoint
        
        Args:
            active_mw: Active power setpoint in MW
            reactive_mvar: Reactive power setpoint in MVAR (optional)
        
        Returns: Result dict
        """
        # Validate range
        min_p, max_p = self.operating_ranges['active_power_mw']
        if not (min_p <= active_mw <= max_p):
            return {
                'success': False,
                'error': f'Active power setpoint must be between {min_p} and {max_p} MW'
            }
        
        old_setpoint = self.power_setpoint_mw
        self.power_setpoint_mw = active_mw
        
        if reactive_mvar is not None:
            min_q, max_q = self.operating_ranges['reactive_power_mvar']
            if not (min_q <= reactive_mvar <= max_q):
                return {
                    'success': False,
                    'error': f'Reactive power setpoint must be between {min_q} and {max_q} MVAR'
                }
            self.reactive_setpoint_mvar = reactive_mvar
        
        logger.info(f"{self.node_id} setpoint changed: {old_setpoint:.1f} -> {active_mw:.1f} MW")
        
        return {
            'success': True,
            'action': 'setpoint_changed',
            'old_setpoint_mw': old_setpoint,
            'new_setpoint_mw': active_mw,
            'reactive_mvar': self.reactive_setpoint_mvar
        }
    
    def reset_relay(self) -> Dict[str, Any]:
        """Reset tripped relay (after fault cleared)"""
        if not self.state.relay_trip:
            return {'success': False, 'error': 'Relay is not tripped'}
        
        self.state.relay_trip = False
        logger.info(f"{self.node_id} relay reset")
        
        return {'success': True, 'action': 'relay_reset'}
