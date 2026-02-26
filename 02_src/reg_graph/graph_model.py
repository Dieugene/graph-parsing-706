"""LPG data model primitives for the pipeline scaffold."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GraphNode:
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    id: str
    type: str
    source: str
    target: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphState:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: Dict[str, GraphEdge] = field(default_factory=dict)
    pending_refs: List[Dict[str, Any]] = field(default_factory=list)
    fz_questions: List[Dict[str, Any]] = field(default_factory=list)
