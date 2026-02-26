# Python core scaffold: pipeline, LPG model, orchestrator, CLI

## Что нужно сделать

Реализовать стартовый исполняемый каркас системы в `02_src/`:
- пакет с моделями графа (узлы, рёбра, состояние графа);
- оркестратор графа с API upsert/add edge/pending refs;
- каркас фаз конвейера и раннер;
- CLI-команду для запуска и сохранения артефактов JSON в `03_data/`.

Текущая задача ограничена детерминированным слоем и заглушками фаз, без LLM-интеграции и без отдельного парсинга внешних ФЗ.

## Зачем

Нужен минимальный рабочий контур, чтобы:
- зафиксировать контракты между фазами;
- начать накапливать проверяемые артефакты (`graph.json`, `pending_refs`, `fz_questions`);
- обеспечить техническую базу для последующих итераций без архитектурной переделки.

## Acceptance Criteria

- [ ] AC-1: В `02_src/` создан Python-пакет с базовыми моделями LPG (`GraphNode`, `GraphEdge`, `GraphState`).
- [ ] AC-2: Реализован `GraphOrchestrator` с методами:
  - `add_or_update_node(node_type, natural_key, properties) -> node_id`
  - `add_edge(edge_type, source_id, target_id, properties) -> edge_id`
  - `add_pending_ref(source_id, ref_text, context)`
  - `to_json() -> dict`
- [ ] AC-3: Реализован `PipelineRunner`, который выполняет фазы последовательно и передает контекст.
- [ ] AC-4: Реализован CLI-скрипт, который запускает раннер и сохраняет JSON-артефакт в `03_data/`.
- [ ] AC-5: В артефакте присутствуют секции `nodes`, `edges`, `pending_refs`, `fz_questions`.
- [ ] AC-6: Фаза extraction на этом шаге реализована как stub и может добавлять демонстрационные записи без сетевых вызовов.

## Контекст

**Релевантные части архитектуры (из `00_docs/architecture/overview.md`):**

- Конвейер состоит из фаз:
  1) DocumentIngestion
  2) AppendixStructureExtractor
  3) IncrementalKnowledgeExtraction
  4) ReferenceResolver
  5) ValidationAndQA
- Графовая модель: Labeled Property Graph.
- Базовые типы узлов: `registration_action`, `document`, `security_type`, `factor`, `factor_value`, `document_section`, `document_field`, `field_group`, `legal_reference`.
- Важно разделение ответственности: LLM отвечает за интерпретацию текста, алгоритм/оркестратор за детерминированное состояние графа и ID.
- В сервисных артефактах должны поддерживаться `pending_refs` и `fz_questions`.

**Релевантные ADR:**

На момент постановки задачи файлы `00_docs/architecture/decision_*.md` отсутствуют. Архитектурные решения берутся напрямую из `overview.md`, без изменений.

**Implementation Plan (Iteration 1):**

Цель итерации: поднять исполняемый Python-каркас конвейера, модели LPG и оркестратор состояния без LLM-слоя.

**Интерфейсы и контракты (ПОЛНОСТЬЮ):**

```python
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
```

```python
class GraphOrchestrator:
    def add_or_update_node(self, node_type: str, natural_key: str, properties: dict) -> str: ...
    def add_edge(self, edge_type: str, source_id: str, target_id: str, properties: dict) -> str: ...
    def add_pending_ref(self, source_id: str, ref_text: str, context: dict) -> None: ...
    def to_json(self) -> dict: ...
```

```python
class PipelinePhase:
    phase_name: str
    def run(self, context: dict) -> dict: ...
```

**Контракты обмена между модулями:**

```python
ingestion_output = {
    "paragraph_index": dict,
    "appendix_index": dict,
    "traversal_plan": list[dict],
}
```

```python
extraction_output = {
    "nodes": list[dict],
    "edges": list[dict],
    "references": list[dict],
    "fz_questions": list[dict],
}
```

```python
resolver_input = {
    "graph_state": dict,
    "pending_refs": list[dict],
}
```

**Гарантии контрактов:**
- Каждый добавляемый факт должен быть трассируемым к `legal_ref`.
- Идентификаторы `id` создает только оркестратор.
- Фазы не модифицируют граф напрямую, только через API оркестратора.

**Критерии готовности модуля (из implementation plan):**
- [ ] Фазы конвейера запускаются последовательно в одном `PipelineRunner`.
- [ ] Граф и оркестратор сериализуют результат в JSON.
- [ ] Поддерживаются `pending_refs` и `fz_questions` как сервисные артефакты.
- [ ] Запуск через CLI создает артефакт в `03_data/`.

**Стратегия моков для этой задачи:**
- LLM extraction: stub-фаза с фиксированным/демо выходом.
- DOCX parsing: допускается fallback на упрощенный локальный input.
- Внешние ФЗ: не извлекать, только писать вопросы в `fz_questions`.

**Ограничение по тестам:**
- Не создавать новые тестовые модули, если нет прямого указания пользователя.
- Для проверки работоспособности допускается только ручной smoke-запуск CLI и фиксация результата в отчете.

## Артефакт выполнения от Developer

После реализации создать отчет:
- `01_tasks/001_pipeline_scaffold/implementation_01.md`

В отчете обязательно:
- какие файлы созданы/изменены;
- как запускался smoke-check;
- какие моки/заглушки использованы и как их заменить в следующих итерациях.
