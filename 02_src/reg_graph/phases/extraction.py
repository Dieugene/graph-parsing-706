"""Incremental extraction phase powered by LangGraph + real LLM."""

import json
import os
import re
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from ..graph_orchestrator import GraphOrchestrator
from ..pipeline import PipelinePhase


class ExtractionState(TypedDict):
    paragraph_index: Dict[str, Dict[str, Any]]
    traversal_plan: List[Dict[str, Any]]
    windows: List[Dict[str, Any]]
    raw_model_outputs: List[Dict[str, Any]]
    llm_calls: List[Dict[str, Any]]
    parsed_batches: List[Dict[str, Any]]


class IncrementalKnowledgeExtractionPhase(PipelinePhase):
    phase_name = "extraction"

    def __init__(self, model_name: str = "gpt-4.1-mini", temperature: float = 0.0) -> None:
        self._model_name = model_name
        self._temperature = temperature

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator: GraphOrchestrator = context["orchestrator"]
        ingestion_output = context.get("ingestion_output", {})

        workflow = self._build_workflow()
        result_state = workflow.invoke(
            {
                "paragraph_index": ingestion_output.get("paragraph_index", {}),
                "traversal_plan": ingestion_output.get("traversal_plan", []),
                "windows": [],
                "raw_model_outputs": [],
                "llm_calls": [],
                "parsed_batches": [],
            }
        )

        extraction_output = self._merge_batches(
            result_state.get("parsed_batches", []),
            result_state.get("llm_calls", []),
        )
        self._apply_to_graph(orchestrator, extraction_output)
        return {"extraction_output": extraction_output}

    def _build_workflow(self):
        graph = StateGraph(ExtractionState)
        graph.add_node("prepare_windows", self._prepare_windows)
        graph.add_node("extract_with_llm", self._extract_with_llm)
        graph.add_node("parse_outputs", self._parse_outputs)
        graph.add_edge(START, "prepare_windows")
        graph.add_edge("prepare_windows", "extract_with_llm")
        graph.add_edge("extract_with_llm", "parse_outputs")
        graph.add_edge("parse_outputs", END)
        return graph.compile()

    def _prepare_windows(self, state: ExtractionState) -> Dict[str, Any]:
        paragraph_index = state.get("paragraph_index", {})
        traversal_plan = state.get("traversal_plan", [])
        windows: List[Dict[str, Any]] = []

        for plan_item in traversal_plan:
            paragraph_ids = plan_item.get("paragraph_ids", [])
            chunk: List[Dict[str, str]] = []
            for paragraph_id in paragraph_ids:
                paragraph = paragraph_index.get(paragraph_id)
                if paragraph:
                    chunk.append(
                        {
                            "paragraph_id": paragraph_id,
                            "text": str(paragraph.get("text", "")).strip(),
                            "legal_ref": str(paragraph.get("legal_ref", "")).strip(),
                        }
                    )
            if not chunk:
                continue
            windows.append(
                {
                    "chapter": str(plan_item.get("chapter", "unknown")),
                    "paragraphs": chunk,
                }
            )

        if not windows and paragraph_index:
            fallback = [
                {
                    "paragraph_id": paragraph_id,
                    "text": str(payload.get("text", "")).strip(),
                    "legal_ref": str(payload.get("legal_ref", "")).strip(),
                }
                for paragraph_id, payload in paragraph_index.items()
            ]
            windows = [{"chapter": "fallback", "paragraphs": fallback}]

        return {"windows": windows}

    def _extract_with_llm(self, state: ExtractionState) -> Dict[str, Any]:
        model = self._build_model()
        windows = state.get("windows", [])
        raw_outputs: List[Dict[str, Any]] = []
        llm_calls: List[Dict[str, Any]] = []

        for window in windows:
            prompt = self._build_prompt(window)
            response = model.invoke(prompt)
            response_text = self._to_text(response.content)
            response_metadata = getattr(response, "response_metadata", {}) or {}
            usage = response_metadata.get("token_usage") or getattr(response, "usage_metadata", {})

            raw_outputs.append(
                {
                    "chapter": window.get("chapter", "unknown"),
                    "window": window,
                    "content": response_text,
                }
            )
            llm_calls.append(
                {
                    "chapter": window.get("chapter", "unknown"),
                    "model": response_metadata.get("model_name", self._model_name),
                    "finish_reason": response_metadata.get("finish_reason"),
                    "token_usage": usage,
                }
            )

        return {"raw_model_outputs": raw_outputs, "llm_calls": llm_calls}

    def _parse_outputs(self, state: ExtractionState) -> Dict[str, Any]:
        parsed_batches: List[Dict[str, Any]] = []
        for item in state.get("raw_model_outputs", []):
            chapter = str(item.get("chapter", "unknown"))
            window = item.get("window", {})
            response_text = str(item.get("content", "")).strip()
            legal_ref = self._window_legal_ref(window)

            parsed_payload, parse_error = self._parse_extraction_json(response_text)
            if parse_error:
                parsed_payload = self._fallback_extraction(window)

            normalized = self._normalize_payload(parsed_payload, legal_ref=legal_ref, chapter=chapter)
            if not normalized["references"] and normalized["nodes"]:
                appendix_match = re.match(r"^app_(\d+)$", chapter)
                if appendix_match:
                    normalized["references"].append(
                        {
                            "source_natural_key": normalized["nodes"][0]["natural_key"],
                            "ref_text": f"см. приложение {appendix_match.group(1)}",
                            "context": {"legal_ref": legal_ref},
                        }
                    )
            if parse_error:
                normalized["metadata"] = {"parse_error": parse_error}
            parsed_batches.append(normalized)
        return {"parsed_batches": parsed_batches}

    def _build_model(self) -> ChatOpenAI:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment/.env")

        model_name = os.getenv("OPENAI_MODEL", self._model_name)
        return ChatOpenAI(
            model=model_name,
            temperature=self._temperature,
            api_key=api_key,
            base_url=base_url,
        )

    @staticmethod
    def _build_prompt(window: Dict[str, Any]) -> List[Tuple[str, str]]:
        chapter = window.get("chapter", "unknown")
        paragraph_lines = []
        for paragraph in window.get("paragraphs", []):
            paragraph_lines.append(
                f"[{paragraph.get('paragraph_id')} | {paragraph.get('legal_ref', '')}] {paragraph.get('text', '')}"
            )

        content_block = "\n".join(paragraph_lines) if paragraph_lines else "(empty)"
        system_prompt = (
            "You extract regulatory facts from Russian legal text.\n"
            "Return STRICT JSON only with shape:\n"
            "{"
            '"nodes":[{"type":"...","natural_key":"...","properties":{"name":"...","legal_ref":"..."}}],'
            '"edges":[{"type":"...","source_natural_key":"...","target_natural_key":"...","properties":{"legal_ref":"..."}}],'
            '"references":[{"source_natural_key":"...","ref_text":"...","context":{"legal_ref":"..."}}],'
            '"fz_questions":[{"question":"...","source":"..."}]'
            "}\n"
            "All extracted entities must include legal_ref."
        )
        user_prompt = (
            f"Chapter/window: {chapter}\n"
            f"Paragraphs:\n{content_block}\n\n"
            "Extract only facts explicitly present in text."
        )
        return [("system", system_prompt), ("user", user_prompt)]

    @staticmethod
    def _to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _parse_extraction_json(response_text: str) -> Tuple[Dict[str, Any], str]:
        if not response_text:
            return {}, "empty_response"
        try:
            return json.loads(response_text), ""
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", response_text, flags=re.DOTALL)
            if not match:
                return {}, "json_object_not_found"
            try:
                return json.loads(match.group(0)), ""
            except json.JSONDecodeError as error:
                return {}, f"json_decode_error: {error.msg}"

    @staticmethod
    def _window_legal_ref(window: Dict[str, Any]) -> str:
        refs = [str(par.get("legal_ref", "")).strip() for par in window.get("paragraphs", [])]
        refs = [ref for ref in refs if ref]
        return refs[0] if refs else "706-П"

    @staticmethod
    def _fallback_extraction(window: Dict[str, Any]) -> Dict[str, Any]:
        chapter = str(window.get("chapter", "unknown"))
        legal_ref = IncrementalKnowledgeExtractionPhase._window_legal_ref(window)
        paragraph_text = " ".join(str(par.get("text", "")) for par in window.get("paragraphs", []))
        clean_key = re.sub(r"[^a-zA-Z0-9_]+", "_", chapter).strip("_") or "window"
        action_key = f"action:{clean_key}"
        return {
            "nodes": [
                {
                    "type": "registration_action",
                    "natural_key": action_key,
                    "properties": {"name": f"Извлечено из окна {chapter}", "legal_ref": legal_ref},
                }
            ],
            "edges": [],
            "references": [
                {
                    "source_natural_key": action_key,
                    "ref_text": "авто-референс: требуется ручная проверка",
                    "context": {"legal_ref": legal_ref, "snippet": paragraph_text[:300]},
                }
            ],
            "fz_questions": [
                {
                    "question": "Проверьте корректность извлечения после fallback-парсинга ответа LLM.",
                    "source": legal_ref,
                }
            ],
        }

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any], legal_ref: str, chapter: str) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        for node in payload.get("nodes", []) if isinstance(payload, dict) else []:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("type", "extracted_entity"))
            natural_key = str(node.get("natural_key", f"{node_type}:{chapter}"))
            properties = dict(node.get("properties", {}))
            properties.setdefault("name", natural_key)
            properties.setdefault("legal_ref", legal_ref)
            nodes.append({"type": node_type, "natural_key": natural_key, "properties": properties})

        edges: List[Dict[str, Any]] = []
        for edge in payload.get("edges", []) if isinstance(payload, dict) else []:
            if not isinstance(edge, dict):
                continue
            edge_type = str(edge.get("type", "RELATED_TO"))
            source_key = str(edge.get("source_natural_key", ""))
            target_key = str(edge.get("target_natural_key", ""))
            if not source_key or not target_key:
                continue
            properties = dict(edge.get("properties", {}))
            properties.setdefault("legal_ref", legal_ref)
            edges.append(
                {
                    "type": edge_type,
                    "source_natural_key": source_key,
                    "target_natural_key": target_key,
                    "properties": properties,
                }
            )

        references: List[Dict[str, Any]] = []
        for ref in payload.get("references", []) if isinstance(payload, dict) else []:
            if not isinstance(ref, dict):
                continue
            source_key = str(ref.get("source_natural_key", ""))
            ref_text = str(ref.get("ref_text", "")).strip()
            if not source_key or not ref_text:
                continue
            ref_context = dict(ref.get("context", {}))
            ref_context.setdefault("legal_ref", legal_ref)
            references.append(
                {
                    "source_natural_key": source_key,
                    "ref_text": ref_text,
                    "context": ref_context,
                }
            )

        fz_questions = [
            question
            for question in payload.get("fz_questions", []) if isinstance(payload, dict)
            if isinstance(question, dict)
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "references": references,
            "fz_questions": fz_questions,
        }

    @staticmethod
    def _merge_batches(parsed_batches: List[Dict[str, Any]], llm_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        merged = {"nodes": [], "edges": [], "references": [], "fz_questions": [], "llm_calls": llm_calls}
        for batch in parsed_batches:
            merged["nodes"].extend(batch.get("nodes", []))
            merged["edges"].extend(batch.get("edges", []))
            merged["references"].extend(batch.get("references", []))
            merged["fz_questions"].extend(batch.get("fz_questions", []))
        return merged

    @staticmethod
    def _apply_to_graph(orchestrator: GraphOrchestrator, extraction_output: Dict[str, Any]) -> None:
        node_id_map: Dict[str, str] = {}

        for node_payload in extraction_output.get("nodes", []):
            natural_key = str(node_payload.get("natural_key", "")).strip()
            if not natural_key:
                continue
            node_id = orchestrator.add_or_update_node(
                node_type=str(node_payload.get("type", "extracted_entity")),
                natural_key=natural_key,
                properties=dict(node_payload.get("properties", {})),
            )
            node_id_map[natural_key] = node_id

        def ensure_node_id(natural_key: str, legal_ref: str) -> str:
            node_id = node_id_map.get(natural_key)
            if node_id:
                return node_id
            node_id = orchestrator.add_or_update_node(
                node_type="extracted_entity",
                natural_key=natural_key,
                properties={"name": natural_key, "legal_ref": legal_ref},
            )
            node_id_map[natural_key] = node_id
            return node_id

        for edge_payload in extraction_output.get("edges", []):
            source_key = str(edge_payload.get("source_natural_key", "")).strip()
            target_key = str(edge_payload.get("target_natural_key", "")).strip()
            if not source_key or not target_key:
                continue
            legal_ref = str(edge_payload.get("properties", {}).get("legal_ref", "706-П"))
            source_id = ensure_node_id(source_key, legal_ref)
            target_id = ensure_node_id(target_key, legal_ref)
            orchestrator.add_edge(
                edge_type=str(edge_payload.get("type", "RELATED_TO")),
                source_id=source_id,
                target_id=target_id,
                properties=dict(edge_payload.get("properties", {})),
            )

        for ref_payload in extraction_output.get("references", []):
            source_key = str(ref_payload.get("source_natural_key", "")).strip()
            if not source_key:
                continue
            legal_ref = str(ref_payload.get("context", {}).get("legal_ref", "706-П"))
            source_id = ensure_node_id(source_key, legal_ref)
            orchestrator.add_pending_ref(
                source_id=source_id,
                ref_text=str(ref_payload.get("ref_text", "")),
                context=dict(ref_payload.get("context", {})),
            )

        for question in extraction_output.get("fz_questions", []):
            orchestrator.add_fz_question(dict(question))


# Compatibility alias for references in older docs.
IncrementalKnowledgeExtractionStubPhase = IncrementalKnowledgeExtractionPhase
