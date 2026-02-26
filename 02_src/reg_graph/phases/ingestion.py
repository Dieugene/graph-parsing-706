"""Document ingestion stub phase."""

from typing import Any, Dict

from ..pipeline import PipelinePhase


class DocumentIngestionPhase(PipelinePhase):
    phase_name = "ingestion"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        input_path = context.get("input_path")
        ingestion_output = {
            "paragraph_index": {
                "p_1": {
                    "text": "Регистрация выпуска требует предоставления решения о выпуске.",
                    "legal_ref": "706-П, гл. 1, п. 1.1",
                }
            },
            "appendix_index": {
                "app_1": {
                    "title": "Приложение 1. Перечень документов",
                    "legal_ref": "706-П, приложение 1",
                }
            },
            "traversal_plan": [{"chapter": "1", "paragraph_ids": ["p_1"]}],
        }
        return {"input_path": input_path, "ingestion_output": ingestion_output}
