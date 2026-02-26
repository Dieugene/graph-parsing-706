"""Reference resolver stub phase."""

from typing import Any, Dict

from ..pipeline import PipelinePhase


class ReferenceResolverPhase(PipelinePhase):
    phase_name = "reference_resolver"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        graph_payload = context["orchestrator"].to_json()
        resolver_input = {
            "graph_state": graph_payload,
            "pending_refs": graph_payload["pending_refs"],
        }
        return {"resolver_input": resolver_input, "resolver_output": {"resolved_refs": []}}
