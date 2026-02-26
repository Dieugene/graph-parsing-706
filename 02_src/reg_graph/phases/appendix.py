"""Appendix structure extraction phase."""

from typing import Any, Dict, List

from ..graph_orchestrator import GraphOrchestrator
from ..pipeline import PipelinePhase


class AppendixStructureExtractorPhase(PipelinePhase):
    phase_name = "appendix"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator: GraphOrchestrator = context["orchestrator"]
        ingestion_output = context["ingestion_output"]
        appendix_index = ingestion_output.get("appendix_index", {})

        if not appendix_index:
            appendix_index = {
                "app_1": {
                    "title": "Приложение 1. Перечень документов",
                    "legal_ref": "706-П, приложение 1",
                    "sections": [
                        {
                            "section_code": "1",
                            "title": "Перечень документов",
                            "legal_ref": "706-П, приложение 1",
                            "field_groups": [{"group_code": "group_1", "name": "Основные документы"}],
                            "fields": [
                                {
                                    "field_code": "field_1",
                                    "name": "Копия решения о выпуске",
                                    "required": True,
                                    "legal_ref": "706-П, приложение 1",
                                }
                            ],
                        }
                    ],
                }
            }

        section_ids: List[str] = []
        field_group_ids: List[str] = []
        field_ids: List[str] = []

        for appendix_id, appendix in appendix_index.items():
            legal_ref = appendix.get("legal_ref", f"706-П, {appendix_id}")
            sections = appendix.get("sections") or [
                {
                    "section_code": "1",
                    "title": appendix.get("title", appendix_id),
                    "legal_ref": legal_ref,
                    "field_groups": [],
                    "fields": [],
                }
            ]

            for section in sections:
                section_code = str(section.get("section_code", "1"))
                section_path = f"{appendix_id}.{section_code}"
                section_id = orchestrator.upsert_document_section(
                    appendix_id=appendix_id,
                    section_path=section_path,
                    properties={
                        "title": section.get("title", appendix.get("title", section_path)),
                        "section_code": section_code,
                        "legal_ref": section.get("legal_ref", legal_ref),
                    },
                )
                section_ids.append(section_id)

                groups = section.get("field_groups") or [
                    {
                        "group_code": "group_1",
                        "name": f"Поля раздела {section_code}",
                        "legal_ref": section.get("legal_ref", legal_ref),
                    }
                ]
                for group in groups:
                    group_code = str(group.get("group_code", f"group_{len(field_group_ids) + 1}"))
                    group_id = orchestrator.upsert_field_group(
                        section_id=section_id,
                        group_code=group_code,
                        properties={
                            "name": group.get("name", group_code),
                            "legal_ref": group.get("legal_ref", section.get("legal_ref", legal_ref)),
                        },
                    )
                    field_group_ids.append(group_id)
                    orchestrator.add_edge(
                        edge_type="GROUP_IN_SECTION",
                        source_id=group_id,
                        target_id=section_id,
                        properties={"legal_ref": section.get("legal_ref", legal_ref)},
                    )

                fields = section.get("fields") or [
                    {
                        "field_code": "field_1",
                        "name": section.get("title", "Поле"),
                        "required": True,
                        "legal_ref": section.get("legal_ref", legal_ref),
                    }
                ]
                default_group_id = field_group_ids[-1] if field_group_ids else None
                for field in fields:
                    field_code = str(field.get("field_code", f"field_{len(field_ids) + 1}"))
                    field_id = orchestrator.upsert_document_field(
                        section_id=section_id,
                        field_code=field_code,
                        properties={
                            "name": field.get("name", field_code),
                            "required": bool(field.get("required", True)),
                            "legal_ref": field.get("legal_ref", section.get("legal_ref", legal_ref)),
                        },
                    )
                    field_ids.append(field_id)
                    orchestrator.add_edge(
                        edge_type="BELONGS_TO",
                        source_id=field_id,
                        target_id=section_id,
                        properties={"legal_ref": section.get("legal_ref", legal_ref)},
                    )
                    if default_group_id:
                        orchestrator.add_edge(
                            edge_type="CONTAINS_FIELD",
                            source_id=default_group_id,
                            target_id=field_id,
                            properties={"legal_ref": section.get("legal_ref", legal_ref)},
                        )

        return {
            "appendix_output": {
                "section_ids": section_ids,
                "field_group_ids": field_group_ids,
                "field_ids": field_ids,
            }
        }
