"""Stub pipeline phases for iteration 1 scaffold."""

from .appendix import AppendixStructureExtractorPhase
from .extraction import IncrementalKnowledgeExtractionStubPhase
from .ingestion import DocumentIngestionPhase
from .reference_resolver import ReferenceResolverPhase
from .validation import ValidationAndQAPhase

__all__ = [
    "DocumentIngestionPhase",
    "AppendixStructureExtractorPhase",
    "IncrementalKnowledgeExtractionStubPhase",
    "ReferenceResolverPhase",
    "ValidationAndQAPhase",
]
