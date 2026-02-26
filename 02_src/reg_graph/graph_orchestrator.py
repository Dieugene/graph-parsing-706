"""Deterministic orchestrator for graph state mutations."""

from dataclasses import asdict
from hashlib import sha1
from typing import Any, Dict

from .graph_model import GraphEdge, GraphNode, GraphState


class GraphOrchestrator:
    """Owns identifiers and safe updates of graph state."""

    def __init__(self) -> None:
        self.state = GraphState()
        self._node_registry: Dict[str, str] = {}
        self._edge_registry: Dict[str, str] = {}

    def add_or_update_node(
        self,
        node_type: str,
        natural_key: str,
        properties: Dict[str, Any],
    ) -> str:
        registry_key = f"{node_type}:{natural_key}"
        existing_id = self._node_registry.get(registry_key)
        if existing_id:
            node = self.state.nodes[existing_id]
            node.properties.update(properties)
            return existing_id

        node_id = self._build_id("node", registry_key)
        node = GraphNode(id=node_id, type=node_type, properties=dict(properties))
        self.state.nodes[node_id] = node
        self._node_registry[registry_key] = node_id
        return node_id

    def add_edge(
        self,
        edge_type: str,
        source_id: str,
        target_id: str,
        properties: Dict[str, Any],
    ) -> str:
        if source_id not in self.state.nodes:
            raise ValueError(f"Unknown source node: {source_id}")
        if target_id not in self.state.nodes:
            raise ValueError(f"Unknown target node: {target_id}")

        edge_signature = f"{edge_type}:{source_id}:{target_id}"
        existing_id = self._edge_registry.get(edge_signature)
        if existing_id:
            edge = self.state.edges[existing_id]
            edge.properties.update(properties)
            return existing_id

        edge_id = self._build_id("edge", edge_signature)
        edge = GraphEdge(
            id=edge_id,
            type=edge_type,
            source=source_id,
            target=target_id,
            properties=dict(properties),
        )
        self.state.edges[edge_id] = edge
        self._edge_registry[edge_signature] = edge_id
        return edge_id

    def add_pending_ref(self, source_id: str, ref_text: str, context: Dict[str, Any]) -> None:
        self.state.pending_refs.append(
            {"source_id": source_id, "ref_text": ref_text, "context": dict(context)}
        )

    def replace_pending_refs(self, pending_refs: list[Dict[str, Any]]) -> None:
        self.state.pending_refs = [dict(ref) for ref in pending_refs]

    def add_fz_question(self, question: Dict[str, Any]) -> None:
        self.state.fz_questions.append(dict(question))

    def upsert_document_section(
        self, appendix_id: str, section_path: str, properties: Dict[str, Any]
    ) -> str:
        natural_key = f"{appendix_id}:section:{section_path}"
        merged_properties = {"appendix_id": appendix_id, "section_path": section_path}
        merged_properties.update(properties)
        return self.add_or_update_node(
            node_type="document_section",
            natural_key=natural_key,
            properties=merged_properties,
        )

    def upsert_document_field(
        self, section_id: str, field_code: str, properties: Dict[str, Any]
    ) -> str:
        natural_key = f"{section_id}:field:{field_code}"
        merged_properties = {"section_id": section_id, "field_code": field_code}
        merged_properties.update(properties)
        return self.add_or_update_node(
            node_type="document_field",
            natural_key=natural_key,
            properties=merged_properties,
        )

    def upsert_field_group(
        self, section_id: str, group_code: str, properties: Dict[str, Any]
    ) -> str:
        natural_key = f"{section_id}:group:{group_code}"
        merged_properties = {"section_id": section_id, "group_code": group_code}
        merged_properties.update(properties)
        return self.add_or_update_node(
            node_type="field_group",
            natural_key=natural_key,
            properties=merged_properties,
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "nodes": [asdict(node) for node in self.state.nodes.values()],
            "edges": [asdict(edge) for edge in self.state.edges.values()],
            "pending_refs": list(self.state.pending_refs),
            "fz_questions": list(self.state.fz_questions),
        }

    @staticmethod
    def _build_id(prefix: str, signature: str) -> str:
        digest = sha1(signature.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"
