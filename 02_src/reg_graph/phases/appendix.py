"""Appendix structure extractor stub phase."""

from typing import Any, Dict

from ..graph_orchestrator import GraphOrchestrator
from ..pipeline import PipelinePhase


class AppendixStructureExtractorPhase(PipelinePhase):
    phase_name = "appendix"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator: GraphOrchestrator = context["orchestrator"]
        ingestion_output = context["ingestion_output"]
        appendix = ingestion_output["appendix_index"]["app_1"]

        section_id = orchestrator.add_or_update_node(
            node_type="document_section",
            natural_key="app_1:section:documents",
            properties={
                "title": appendix["title"],
                "section_code": "1",
                "legal_ref": appendix["legal_ref"],
            },
        )
        field_id = orchestrator.add_or_update_node(
            node_type="document_field",
            natural_key="app_1:field:decision_copy",
            properties={
                "name": "Копия решения о выпуске",
                "required": True,
                "legal_ref": appendix["legal_ref"],
            },
        )
        orchestrator.add_edge(
            edge_type="CONTAINS_FIELD",
            source_id=section_id,
            target_id=field_id,
            properties={"legal_ref": appendix["legal_ref"]},
        )

        return {"appendix_output": {"section_ids": [section_id], "field_ids": [field_id]}}
