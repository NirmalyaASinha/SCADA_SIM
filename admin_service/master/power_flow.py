"""
Power flow and cascade computation for SCADA grid topology.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class PowerFlowEngine:
    TOPOLOGY: Dict[str, Dict] = {
        "GEN-001": {
            "type": "generation",
            "feeds": ["SUB-001", "SUB-002", "SUB-003"],
            "fed_by": [],
        },
        "GEN-002": {
            "type": "generation",
            "feeds": ["SUB-001", "SUB-002", "SUB-003"],
            "fed_by": [],
        },
        "SUB-001": {
            "type": "transmission",
            "feeds": ["DIST-001"],
            "fed_by": ["GEN-001", "GEN-002"],
        },
        "SUB-002": {
            "type": "transmission",
            "feeds": ["DIST-002"],
            "fed_by": ["GEN-001", "GEN-002"],
        },
        "SUB-003": {
            "type": "transmission",
            "feeds": [],
            "fed_by": ["GEN-001", "GEN-002"],
        },
        "DIST-001": {
            "type": "distribution",
            "feeds": ["HOUSEHOLDS"],
            "fed_by": ["SUB-001"],
        },
        "DIST-002": {
            "type": "distribution",
            "feeds": ["HOUSEHOLDS"],
            "fed_by": ["SUB-002"],
        },
    }

    CONSUMER_DATA: Dict[str, Dict] = {
        "DIST-001": {
            "households": 45000,
            "area": "North Zone",
            "load_kw": 125000,
        },
        "DIST-002": {
            "households": 38000,
            "area": "South Zone",
            "load_kw": 98000,
        },
    }

    async def compute_cascade(self, tripped_node_id: str, node_states: Dict[str, str]) -> List[str]:
        """
        When a node trips, return ALL nodes that lose power.
        Only de-energize a node if ALL its upstream sources are offline.
        """
        effective_states = dict(node_states or {})
        effective_states[tripped_node_id] = "TRIPPED"

        affected: List[str] = []
        visited = set()
        queue = list(self.TOPOLOGY.get(tripped_node_id, {}).get("feeds", []))

        while queue:
            node_id = queue.pop(0)
            if node_id in visited or node_id == "HOUSEHOLDS":
                continue
            visited.add(node_id)

            if not await self.has_power_source(node_id, effective_states):
                affected.append(node_id)
                queue.extend(self.TOPOLOGY.get(node_id, {}).get("feeds", []))

        return affected

    async def has_power_source(self, node_id: str, node_states: Dict[str, str]) -> bool:
        """
        Returns True if at least one upstream node is ENERGIZED.
        Returns False if ALL upstream nodes are offline/tripped.
        """
        node_info = self.TOPOLOGY.get(node_id)
        if not node_info:
            return False

        upstream = node_info.get("fed_by", [])
        if not upstream:
            return self._is_energized(node_states.get(node_id))

        for upstream_id in upstream:
            if self._is_energized(node_states.get(upstream_id)):
                return True
        return False

    async def get_power_source(self, node_id: str, node_states: Dict[str, str]) -> bool:
        """Compatibility alias for has_power_source."""
        return await self.has_power_source(node_id, node_states)

    async def get_energized_edges(
        self,
        node_states: Dict[str, str],
        node_telemetry: Optional[Dict[str, Dict]] = None,
    ) -> List[Dict]:
        """
        Returns all topology edges with energized=True/False.
        Used by admin dashboard to color transmission lines.
        """
        edges: List[Dict] = []
        telemetry = node_telemetry or {}

        for source_id, info in self.TOPOLOGY.items():
            for target_id in info.get("feeds", []):
                if target_id == "HOUSEHOLDS":
                    continue

                source_energized = self._is_energized(node_states.get(source_id))
                target_has_power = await self.has_power_source(target_id, node_states)

                power_mw = 0.0
                source_telemetry = telemetry.get(source_id)
                if source_telemetry:
                    try:
                        power_mw = float(source_telemetry.get("active_power_mw", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        power_mw = 0.0

                edges.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "energized": source_energized and target_has_power,
                        "power_mw": power_mw,
                    }
                )

        return edges

    async def get_households_affected(self, affected_nodes: List[str]) -> int:
        """Sum of households for all DIST nodes in affected_nodes list."""
        total = 0
        for node_id in affected_nodes:
            data = self.CONSUMER_DATA.get(node_id)
            if data:
                total += int(data.get("households", 0))
        return total

    def _normalize_state(self, state: Optional[str]) -> str:
        if not state:
            return "UNKNOWN"
        state_upper = state.upper()
        if state_upper in {"NORMAL", "ONLINE"}:
            return "ENERGIZED"
        return state_upper

    def _is_energized(self, state: Optional[str]) -> bool:
        return self._normalize_state(state) == "ENERGIZED"
