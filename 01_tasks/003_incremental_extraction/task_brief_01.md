# Incremental extraction + lifecycle pending_refs (LangGraph + real LLM)

## Что нужно сделать

Реализовать первый рабочий контур инкрементального извлечения фактов по окнам текста с использованием реального LLM (без моков), а также жизненный цикл `pending_refs`.

Объем задачи:
- заменить `IncrementalKnowledgeExtractionStubPhase` на реальную фазу extraction;
- реализовать LangGraph-узел/граф для extraction шага на Python;
- использовать `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`) для реальных вызовов LLM через `langchain-openai`;
- реализовать `ReferenceResolverPhase` с базовой попыткой резолва ссылок по существующим узлам и сохранением нерезолвленных ссылок;
- обеспечить прогон на малом входе (small sample) в `.venv`.

## Зачем

Это первый этап, где конвейер начинает извлекать факты не из заглушек, а из реального текста и реального LLM, что позволяет:
- быстро проверить качество на небольшом фрагменте документа;
- увидеть реальные `pending_refs` и их частичный резолв;
- подготовить базу для прогона полного документа.

## Acceptance Criteria

- [ ] AC-1: extraction-фаза выполняет реальные LLM-вызовы (без mock-ответов) и формирует выход в контракте `extraction_output`.
- [ ] AC-2: используется LangGraph (Python) для orchestration extraction шага (минимум state + node + compile + invoke/ainvoke).
- [ ] AC-3: LLM-конфигурация читается из `.env` через переменные окружения; секреты не логируются.
- [ ] AC-4: `ReferenceResolverPhase` обрабатывает `pending_refs` и пытается связать их с существующими `document_section/document_field/document` узлами.
- [ ] AC-5: после resolver-фазы нерезолвленные ссылки сохраняются в артефакте (`pending_refs`) с reason/context.
- [ ] AC-6: smoke-прогон через `.venv` на малом входе успешно завершается; в отчете отражены:
  - факт реального LLM-вызова,
  - количество созданных узлов/рёбер,
  - сколько `pending_refs` резолвлено/не резолвлено.
- [ ] AC-7: не создаются тестовые модули (`tests/`, `test_*.py`) без прямого указания пользователя.

## Контекст

**Релевантные части архитектуры:**
- Фаза 3: `IncrementalKnowledgeExtraction` — инкрементальная обработка по окнам.
- Фаза 4: `ReferenceResolver` — разбор `pending_refs`.
- Инварианта: каждая извлеченная сущность должна иметь `legal_ref`.

**Релевантные ADR:**
- На момент задачи `00_docs/architecture/decision_*.md` отсутствуют.

**Implementation Plan (Iteration 3):**
- Реализовать `window_extractor` и `reference_resolver`.
- Временно допускается conservative matching (без агрессивного merge сущностей).

**Интерфейсы и контракты (ПОЛНОСТЬЮ):**

```python
class WindowExtractor:
    def extract_facts(self, chapter_window: dict, context_slice: dict) -> dict: ...

class ReferenceResolver:
    def resolve(self, pending_refs: list[dict], graph_state: dict) -> dict: ...
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

## Технические указания

- Работать только в `.venv`.
- Для LangGraph использовать актуальный Python API (ориентир — docs.langchain.com, полученные через MCP `user-docs-langchain`):
  - `from langgraph.graph import StateGraph, START, END`
  - state schema через `TypedDict`/`Annotated` или эквивалент.
- Для LLM использовать `langchain-openai` (`ChatOpenAI`) с переменными окружения из `.env`.
- Не добавлять моки на LLM.

## Существующий код для reference

- `02_src/reg_graph/phases/extraction.py`
- `02_src/reg_graph/phases/reference_resolver.py`
- `02_src/reg_graph/phases/ingestion.py`
- `02_src/reg_graph/graph_orchestrator.py`
- `02_src/reg_graph/cli.py`

## Артефакт выполнения от Developer

После реализации создать:
- `01_tasks/003_incremental_extraction/implementation_01.md`

В отчете обязательно:
- список изменений;
- команда smoke-прогона в `.venv`;
- подтверждение реального LLM-вызова;
- список оставшихся ограничений перед полным прогоном документа.
