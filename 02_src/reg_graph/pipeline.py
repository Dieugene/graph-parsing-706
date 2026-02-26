"""Pipeline abstractions and sequential runner."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List


class PipelinePhase(ABC):
    phase_name: str

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class PipelineRunner:
    def __init__(self, phases: Iterable[PipelinePhase]) -> None:
        self.phases: List[PipelinePhase] = list(phases)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        current = dict(context)
        for phase in self.phases:
            phase_result = phase.run(current)
            if not isinstance(phase_result, dict):
                raise TypeError(f"Phase '{phase.phase_name}' must return dict context.")
            current.update(phase_result)
        return current
