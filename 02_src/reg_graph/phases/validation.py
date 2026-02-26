"""Validation and QA stub phase."""

from typing import Any, Dict

from ..pipeline import PipelinePhase


class ValidationAndQAPhase(PipelinePhase):
    phase_name = "validation"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        graph_payload = context["orchestrator"].to_json()
        qa_report = {
            "node_count": len(graph_payload["nodes"]),
            "edge_count": len(graph_payload["edges"]),
            "pending_ref_count": len(graph_payload["pending_refs"]),
            "fz_question_count": len(graph_payload["fz_questions"]),
            "warnings": [],
        }
        return {"validation_report": qa_report}
