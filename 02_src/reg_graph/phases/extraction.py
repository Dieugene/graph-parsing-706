"""Incremental extraction stub phase."""

from typing import Any, Dict, List

from ..graph_orchestrator import GraphOrchestrator
from ..pipeline import PipelinePhase


class IncrementalKnowledgeExtractionStubPhase(PipelinePhase):
    phase_name = "extraction"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator: GraphOrchestrator = context["orchestrator"]
        extraction_output = self._build_stub_output()

        node_id_map: Dict[str, str] = {}
        for node_payload in extraction_output["nodes"]:
            node_id = orchestrator.add_or_update_node(
                node_type=node_payload["type"],
                natural_key=node_payload["natural_key"],
                properties=node_payload["properties"],
            )
            node_id_map[node_payload["natural_key"]] = node_id

        for edge_payload in extraction_output["edges"]:
            orchestrator.add_edge(
                edge_type=edge_payload["type"],
                source_id=node_id_map[edge_payload["source_natural_key"]],
                target_id=node_id_map[edge_payload["target_natural_key"]],
                properties=edge_payload["properties"],
            )

        for ref_payload in extraction_output["references"]:
            orchestrator.add_pending_ref(
                source_id=node_id_map[ref_payload["source_natural_key"]],
                ref_text=ref_payload["ref_text"],
                context=ref_payload["context"],
            )

        for question in extraction_output["fz_questions"]:
            orchestrator.add_fz_question(question)

        return {"extraction_output": extraction_output}

    @staticmethod
    def _build_stub_output() -> Dict[str, List[Dict[str, Any]]]:
        return {
            "nodes": [
                {
                    "type": "registration_action",
                    "natural_key": "action:issue_registration",
                    "properties": {
                        "name": "Регистрация выпуска",
                        "legal_ref": "706-П, гл. 1, п. 1.1",
                    },
                },
                {
                    "type": "document",
                    "natural_key": "document:issue_decision",
                    "properties": {
                        "name": "Решение о выпуске",
                        "legal_ref": "706-П, приложение 1",
                    },
                },
            ],
            "edges": [
                {
                    "type": "REQUIRES_DOCUMENT",
                    "source_natural_key": "action:issue_registration",
                    "target_natural_key": "document:issue_decision",
                    "properties": {"legal_ref": "706-П, гл. 1, п. 1.1"},
                }
            ],
            "references": [
                {
                    "source_natural_key": "action:issue_registration",
                    "ref_text": "см. Федеральный закон о рынке ценных бумаг",
                    "context": {"legal_ref": "706-П, гл. 1, п. 1.1"},
                }
            ],
            "fz_questions": [
                {
                    "question": "Нужно уточнить актуальную статью ФЗ для требования.",
                    "source": "706-П, гл. 1, п. 1.1",
                }
            ],
        }
