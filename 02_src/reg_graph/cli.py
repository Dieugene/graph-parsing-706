"""CLI entrypoint helpers for scaffold pipeline run."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from .graph_orchestrator import GraphOrchestrator
from .phases import (
    AppendixStructureExtractorPhase,
    DocumentIngestionPhase,
    IncrementalKnowledgeExtractionStubPhase,
    ReferenceResolverPhase,
    ValidationAndQAPhase,
)
from .pipeline import PipelinePhase, PipelineRunner


def build_default_phases() -> List[PipelinePhase]:
    return [
        DocumentIngestionPhase(),
        AppendixStructureExtractorPhase(),
        IncrementalKnowledgeExtractionStubPhase(),
        ReferenceResolverPhase(),
        ValidationAndQAPhase(),
    ]


def run_pipeline(input_path: str = "") -> Dict[str, Any]:
    orchestrator = GraphOrchestrator()
    initial_context: Dict[str, Any] = {
        "input_path": input_path,
        "orchestrator": orchestrator,
    }
    runner = PipelineRunner(phases=build_default_phases())
    final_context = runner.run(initial_context)
    artifact = orchestrator.to_json()
    artifact["meta"] = {
        "input_path": input_path,
        "validation_report": final_context.get("validation_report", {}),
    }
    return artifact


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pipeline scaffold and save JSON artifact.")
    parser.add_argument(
        "--input-path",
        default="",
        help="Optional path to source DOCX for real ingestion parsing.",
    )
    parser.add_argument(
        "--output-path",
        default="03_data/01_pipeline_scaffold/graph_artifact.json",
        help="Where to save resulting graph artifact JSON.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = run_pipeline(input_path=args.input_path)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pipeline scaffold artifact saved to: {output_path.resolve()}")
    print(
        "Counts:",
        f"nodes={len(artifact['nodes'])}",
        f"edges={len(artifact['edges'])}",
        f"pending_refs={len(artifact['pending_refs'])}",
        f"fz_questions={len(artifact['fz_questions'])}",
    )
    return 0
