"""Reference resolver phase with conservative matching."""

import re
from typing import Any, Dict, List

from ..graph_orchestrator import GraphOrchestrator
from ..pipeline import PipelinePhase


class ReferenceResolverPhase(PipelinePhase):
    phase_name = "reference_resolver"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator: GraphOrchestrator = context["orchestrator"]
        graph_payload = orchestrator.to_json()
        resolver_input = {
            "graph_state": graph_payload,
            "pending_refs": graph_payload["pending_refs"],
        }

        node_ids = {node["id"] for node in graph_payload.get("nodes", [])}
        candidates = self._build_candidates(graph_payload.get("nodes", []))
        resolved_refs: List[Dict[str, Any]] = []
        unresolved_refs: List[Dict[str, Any]] = []

        for ref in graph_payload.get("pending_refs", []):
            source_id = str(ref.get("source_id", ""))
            ref_text = str(ref.get("ref_text", "")).strip()
            ref_context = dict(ref.get("context", {}))
            legal_ref = str(ref_context.get("legal_ref", "706-П"))

            if not source_id or source_id not in node_ids:
                unresolved_refs.append(
                    {
                        **ref,
                        "reason": "source_not_found",
                        "context": {**ref_context, "resolver": "reference_resolver"},
                    }
                )
                continue
            if not ref_text:
                unresolved_refs.append(
                    {
                        **ref,
                        "reason": "empty_ref_text",
                        "context": {**ref_context, "resolver": "reference_resolver"},
                    }
                )
                continue

            target = self._match_candidate(ref_text, candidates)
            if target is None:
                unresolved_refs.append(
                    {
                        **ref,
                        "reason": "no_candidate_match",
                        "context": {**ref_context, "resolver": "reference_resolver"},
                    }
                )
                continue

            edge_id = orchestrator.add_edge(
                edge_type="REFERENCES",
                source_id=source_id,
                target_id=target["id"],
                properties={
                    "legal_ref": legal_ref,
                    "resolver": "reference_resolver",
                    "ref_text": ref_text,
                    "target_type": target["type"],
                },
            )
            resolved_refs.append(
                {
                    "source_id": source_id,
                    "target_id": target["id"],
                    "target_type": target["type"],
                    "ref_text": ref_text,
                    "edge_id": edge_id,
                }
            )

        orchestrator.replace_pending_refs(unresolved_refs)
        resolver_output = {
            "resolved_refs": resolved_refs,
            "unresolved_refs": unresolved_refs,
            "summary": {
                "input_count": len(graph_payload.get("pending_refs", [])),
                "resolved_count": len(resolved_refs),
                "unresolved_count": len(unresolved_refs),
            },
        }
        return {"resolver_input": resolver_input, "resolver_output": resolver_output}

    @staticmethod
    def _build_candidates(nodes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        allowed_types = {"document_section", "document_field", "document"}
        candidates: List[Dict[str, str]] = []
        for node in nodes:
            node_type = str(node.get("type", ""))
            if node_type not in allowed_types:
                continue
            props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
            appendix_id = str(props.get("appendix_id", ""))
            appendix_label = ""
            appendix_match = re.match(r"app_(\d+)", appendix_id)
            if appendix_match:
                appendix_label = f"приложение {appendix_match.group(1)}"
            searchable_parts = [
                node_type,
                str(props.get("name", "")),
                str(props.get("title", "")),
                str(props.get("section_path", "")),
                str(props.get("field_code", "")),
                appendix_id,
                appendix_label,
            ]
            searchable_text = " ".join(part for part in searchable_parts if part).lower()
            candidates.append(
                {
                    "id": str(node.get("id", "")),
                    "type": node_type,
                    "searchable_text": searchable_text,
                }
            )
        return candidates

    @staticmethod
    def _match_candidate(ref_text: str, candidates: List[Dict[str, str]]) -> Dict[str, str] | None:
        tokens = [token for token in re.findall(r"[a-zа-я0-9_]+", ref_text.lower()) if len(token) >= 3]
        if not tokens:
            return None

        best_candidate: Dict[str, str] | None = None
        best_score = 0
        for candidate in candidates:
            searchable = candidate["searchable_text"]
            score = sum(1 for token in tokens if token in searchable)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate if best_score > 0 else None
