"""
Substation Node Simulation
Simulates transmission substations with transformers
"""

import logging
import random
from typing import Dict, Any

from .base_node import BaseNode, AlarmConfig

logger = logging.getLogger(__name__)


class SubstationNode(BaseNode):
    """
    Substation (transmission) node simulation
    
    Parameters simulated:
    - bus_voltage_kv: 33-132 kV (nominal 132 kV)
    - line_current_a: 200-1500 A (nominal 800 A)
    - active_power_mw: 20-400 MW (nominal 200 MW)
    - reactive_power_mvar: 5-80 MVAR (nominal 30 MVAR)
    - transformer_temp_c: 35-95°C (nominal 65°C)
    - tap_position: 1-17 (nominal 9)
    - power_factor: 0.85-0.99 (nominal 0.95)
    - breaker_state, relay_trip, earth_fault
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        super().__init__(node_id, "transmission", config)
        
        # Nominal operating points
        self.nominal_values = {
            'bus_voltage_kv': 132.0,
            'line_current_a': 800.0,
            'active_power_mw': 200.0,
            'reactive_power_mvar': 30.0,
            'transformer_temp_c': 65.0,
            'tap_position': 9,
            'power_factor': 0.95,
        }
        
        # Operating ranges
        self.operating_ranges = {
            'bus_voltage_kv': (33.0, 132.0),
            'line_current_a': (200.0, 1500.0),
            'active_power_mw': (20.0, 400.0),
            'reactive_power_mvar': (5.0, 80.0),
            'transformer_temp_c': (35.0, 95.0),
            'tap_position': (1, 17),
            'power_factor': (0.85, 0.99),
        }
        
        # Set initial state
        self.state.bus_voltage_kv = self.nominal_values['bus_voltage_kv']
        self.state.line_current_a = self.nominal_values['line_current_a']
        self.state.active_power_mw = self.nominal_values['active_power_mw']
        self.state.reactive_power_mvar = self.nominal_values['reactive_power_mvar']
        self.state.transformer_temp_c = self.nominal_values['transformer_temp_c']
        self.state.tap_position = self.nominal_values['tap_position']
        self.state.power_factor = self.nominal_values['power_factor']
        self.state.breaker_state = True
        self.state.relay_trip = False
        self.state.earth_fault = False
        
        # Configure alarms
        self.alarm_configs = [
            AlarmConfig(
                tag='bus_voltage_kv',
                priority=2,
                high_limit=138.0,
                low_limit=120.0,
                message_template="Bus voltage {value:.2f} kV out of limits"
            ),
            AlarmConfig(
                tag='line_current_a',
                priority=2,
                high_limit=1400.0,
                low_limit=None,
                message_template="Line current {value:.1f} A exceeds limit"
            ),
            AlarmConfig(
                tag='transformer_temp_c',
                priority=1,
                high_limit=85.0,
                low_limit=None,
                message_template="Transformer temperature {value:.1f}°C exceeds limit"
            ),
            AlarmConfig(
                tag='transformer_temp_c',
                priority=2,
                high_limit=75.0,
                low_limit=None,
                message_template="Transformer temperature {value:.1f}°C warning"
            ),
            AlarmConfig(
                tag='power_factor',
                priority=3,
                high_limit=None,
                low_limit=0.88,
                message_template="Power factor {value:.3f} below limit"
            ),
        ]
        
        # Thermal state for temperature simulation
        self._previous_temp = self.nominal_values['transformer_temp_c']
        
        # Earth fault simulation (random rare events)
        self._fault_probability = 0.0001  # 0.01% per simulation step
        
        logger.info(f"SubstationNode {node_id} initialized")
    
    async def update_simulation(self):
        """Update substation node simulation"""
        
        # Get load factor (time of day)
        load_factor = self.get_load_factor()
        
        # If breaker is open, reduce power to zero
        if not self.state.breaker_state or self.state.relay_trip or self.state.earth_fault:
            target_power = 0.0
            target_current = 0.0
            target_temp = 35.0  # Ambient temperature
        else:
            # Normal operation - follows load curve
            target_power = self.nominal_values['active_power_mw'] * load_factor
            target_reactive = self.nominal_values['reactive_power_mvar'] * load_factor
            
            # Voltage regulation based on tap position
            # Each tap step is approximately 1.25% voltage adjustment
            tap_pos = self.state.tap_position if self.state.tap_position is not None else 9
            tap_offset = (tap_pos - 9) * 1.65  # kV per tap
            target_voltage = self.nominal_values['bus_voltage_kv'] + tap_offset
            
            # Calculate current from power
            pf = self.nominal_values['power_factor']
            target_current = (target_power * 1000) / (1.732 * target_voltage * pf)
            
            # Transformer temperature depends on load
            # Temperature rises with I² losses
            load_ratio = target_power / self.nominal_values['active_power_mw']
            target_temp = 35.0 + 40.0 * (load_ratio ** 1.5)  # Non-linear heating
        
        # Update voltage with tap adjustment and noise
        tap_pos = self.state.tap_position if self.state.tap_position is not None else 9
        tap_voltage = self.nominal_values['bus_voltage_kv'] + (tap_pos - 9) * 1.65
        self.state.bus_voltage_kv = self.add_noise(tap_voltage, self.nominal_values['bus_voltage_kv'])
        
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
        
        target_reactive = self.nominal_values['reactive_power_mvar'] * load_factor if target_power > 0 else 0.0
        self.state.reactive_power_mvar = self.add_noise(
            target_reactive,
            self.nominal_values['reactive_power_mvar']
        )
        
        # Update current with noise
        self.state.line_current_a = self.add_noise(
            target_current,
            self.nominal_values['line_current_a']
        )
        
        # Update transformer temperature with thermal lag
        self.state.transformer_temp_c = self.simulate_thermal_lag(
            target_temp,
            self._previous_temp
        )
        self._previous_temp = self.state.transformer_temp_c
        
        # Add noise to temperature
        self.state.transformer_temp_c = self.add_noise(
            self.state.transformer_temp_c,
            self.nominal_values['transformer_temp_c']
        )
        
        # Calculate power factor
        if self.state.active_power_mw > 0:
            apparent_power = (self.state.active_power_mw ** 2 + 
                            self.state.reactive_power_mvar ** 2) ** 0.5
            self.state.power_factor = self.state.active_power_mw / apparent_power
        else:
            self.state.power_factor = 0.0
        
        # Simulate random earth faults (very rare)
        if not self.state.earth_fault and random.random() < self._fault_probability:
            self.state.earth_fault = True
            self.state.relay_trip = True
            logger.error(f"{self.node_id} EARTH FAULT detected!")
        
        # Protection logic
        # Over-current protection
        if self.state.line_current_a > 1450:
            self.state.relay_trip = True
            logger.error(f"{self.node_id} relay tripped: over-current {self.state.line_current_a:.1f} A")
        
        # Over-temperature protection
        if self.state.transformer_temp_c > 90.0:
            self.state.relay_trip = True
            logger.error(f"{self.node_id} relay tripped: over-temperature {self.state.transformer_temp_c:.1f}°C")
    
    def set_tap_position(self, position: int, reason: str = "Operator command") -> Dict[str, Any]:
        """
        Set transformer tap changer position
        
        Args:
            position: Tap position (1-17)
            reason: Reason for the action
        
        Returns: Result dict
        """
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
    
    def clear_earth_fault(self) -> Dict[str, Any]:
        """Clear earth fault (after physical inspection/repair)"""
        if not self.state.earth_fault:
            return {'success': False, 'error': 'No earth fault active'}
        
        self.state.earth_fault = False
        self.state.relay_trip = False
        logger.info(f"{self.node_id} earth fault cleared")
        
        return {'success': True, 'action': 'earth_fault_cleared'}
    
    def reset_relay(self) -> Dict[str, Any]:
        """Reset tripped relay (after fault cleared)"""
        if not self.state.relay_trip:
            return {'success': False, 'error': 'Relay is not tripped'}
        
        # Don't allow reset if earth fault is still active
        if self.state.earth_fault:
            return {
                'success': False,
                'error': 'Cannot reset relay while earth fault is active'
            }
        
        self.state.relay_trip = False
        logger.info(f"{self.node_id} relay reset")
        
        return {'success': True, 'action': 'relay_reset'}
