"""Document ingestion phase with DOCX support and fallback stub."""

from pathlib import Path
import re
from typing import Any, Dict, List

from ..pipeline import PipelinePhase


class DocumentIngestionPhase(PipelinePhase):
    phase_name = "ingestion"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        input_path = context.get("input_path")
        if input_path:
            parsed = self._parse_docx(Path(str(input_path)))
            if parsed is not None:
                return {"input_path": input_path, "ingestion_output": parsed}
        return {"input_path": input_path, "ingestion_output": self._build_fallback_output()}

    def _build_fallback_output(self) -> Dict[str, Any]:
        return {
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

    def _parse_docx(self, input_path: Path) -> Dict[str, Any] | None:
        if not input_path.exists():
            return None

        try:
            from docx import Document  # type: ignore
        except ImportError:
            return None

        document = Document(str(input_path))
        paragraph_index: Dict[str, Dict[str, str]] = {}
        appendix_index: Dict[str, Dict[str, Any]] = {}
        traversal_plan: List[Dict[str, Any]] = []

        paragraph_counter = 0
        current_appendix: Dict[str, Any] | None = None
        current_section: Dict[str, Any] | None = None

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            paragraph_counter += 1
            paragraph_id = f"p_{paragraph_counter}"
            paragraph_index[paragraph_id] = {
                "text": text,
                "legal_ref": f"706-П, абз. {paragraph_counter}",
            }

            appendix_match = re.match(r"^\s*приложение\s+(\d+)", text, flags=re.IGNORECASE)
            if appendix_match:
                appendix_no = appendix_match.group(1)
                appendix_id = f"app_{appendix_no}"
                current_appendix = {
                    "title": text,
                    "legal_ref": f"706-П, приложение {appendix_no}",
                    "sections": [],
                }
                appendix_index[appendix_id] = current_appendix
                current_section = None
                continue

            if current_appendix is None:
                continue

            section_match = re.match(r"^(\d+(?:\.\d+)*)[\)\.\s-]+(.+)$", text)
            if section_match:
                section_code = section_match.group(1)
                section_title = section_match.group(2).strip()
                current_section = {
                    "section_code": section_code,
                    "title": section_title,
                    "legal_ref": current_appendix["legal_ref"],
                    "field_groups": [],
                    "fields": [],
                }
                current_appendix["sections"].append(current_section)
                continue

            if current_section is None:
                current_section = {
                    "section_code": "1",
                    "title": "Общие сведения",
                    "legal_ref": current_appendix["legal_ref"],
                    "field_groups": [],
                    "fields": [],
                }
                current_appendix["sections"].append(current_section)

            group_match = re.match(r"^(?:группа|раздел)\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE)
            if group_match:
                group_name = group_match.group(1).strip()
                group_code = f"group_{len(current_section['field_groups']) + 1}"
                current_section["field_groups"].append(
                    {
                        "group_code": group_code,
                        "name": group_name,
                        "legal_ref": current_appendix["legal_ref"],
                    }
                )
                continue

            field_match = re.match(r"^(?:[-*]\s+|поле\s*[:\-]\s*)(.+)$", text, flags=re.IGNORECASE)
            if field_match:
                field_name = field_match.group(1).strip()
                field_code = f"field_{len(current_section['fields']) + 1}"
                current_section["fields"].append(
                    {
                        "field_code": field_code,
                        "name": field_name,
                        "required": True,
                        "legal_ref": current_appendix["legal_ref"],
                    }
                )
                continue

            if current_section["fields"]:
                continue

            # If no explicit field markers exist, keep first content line as a field.
            current_section["fields"].append(
                {
                    "field_code": "field_1",
                    "name": text,
                    "required": True,
                    "legal_ref": current_appendix["legal_ref"],
                }
            )

        if not paragraph_index:
            return None
        if not appendix_index:
            return {
                "paragraph_index": paragraph_index,
                "appendix_index": {},
                "traversal_plan": [{"chapter": "1", "paragraph_ids": list(paragraph_index.keys())}],
            }

        for appendix_id, appendix in appendix_index.items():
            appendix_fields = sum(len(section["fields"]) for section in appendix["sections"])
            traversal_plan.append(
                {
                    "chapter": appendix_id,
                    "paragraph_ids": list(paragraph_index.keys()),
                    "appendix_field_count": appendix_fields,
                }
            )

        return {
            "paragraph_index": paragraph_index,
            "appendix_index": appendix_index,
            "traversal_plan": traversal_plan,
        }
