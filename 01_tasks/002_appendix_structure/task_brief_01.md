# Appendix structure extraction и подграф форм

## Что нужно сделать

Расширить текущий каркас конвейера так, чтобы:
- `DocumentIngestion` умел читать реальный DOCX (через `python-docx`) и формировать базовый индекс приложений;
- `AppendixStructureExtractor` строил подграф форм приложений (`document_section`, `document_field`, `field_group`) в `GraphOrchestrator`;
- запуск пайплайна на малом входе (small sample) давал наблюдаемый результат в JSON.

## Зачем

Нужно перейти от чистого scaffold к первой предметной полезности:
- получать реальную структуру приложений из текста документа;
- видеть в графе секции и поля форм, на которые далее будут ссылаться требования глав;
- подготовить базу для быстрого прогона сначала на небольшом фрагменте, затем на полном документе.

## Acceptance Criteria

- [ ] AC-1: `DocumentIngestionPhase` поддерживает чтение `--input-path` DOCX и заполняет `appendix_index` на основе реального документа.
- [ ] AC-2: `AppendixStructureExtractorPhase` создает/обновляет узлы типов `document_section`, `document_field`, `field_group` через API оркестратора.
- [ ] AC-3: Для созданных узлов сохраняется `legal_ref` (минимум ссылка на приложение/заголовок).
- [ ] AC-4: В `graph_artifact.json` после запуска появляются узлы по приложениям (не только stub-узлы extraction-фазы).
- [ ] AC-5: Реализован smoke-прогон в venv на небольшом входе (малый DOCX-фрагмент или программно созданный mini DOCX), результат отражен в `implementation_01.md`.
- [ ] AC-6: Не создаются тестовые модули (`tests/`, `test_*.py`) без прямого указания пользователя.

## Контекст

**Релевантные части архитектуры:**
- Фаза 1: `DocumentIngestion` — парсинг DOCX и индексация пунктов/приложений.
- Фаза 2: `AppendixStructureExtractor` — извлечение структуры форм из приложений.
- Подграф приложений должен быть построен до основной extraction-фазы.

**Релевантные ADR:**
- На момент задачи `00_docs/architecture/decision_*.md` отсутствуют.

**Implementation Plan (Iteration 2):**
- Реализовать `appendix_structure_extractor` и расширить оркестратор для узлов структуры форм.
- Для неясных/утраченных элементов — фиксировать предупреждения, не ломать прогон.

**Интерфейсы и контракты (ПОЛНОСТЬЮ):**

```python
class AppendixStructureExtractor:
    def extract(self, appendix_index: dict) -> list[dict]: ...

class GraphOrchestrator:
    def upsert_document_section(self, appendix_id: str, section_path: str, properties: dict) -> str: ...
    def upsert_document_field(self, section_id: str, field_code: str, properties: dict) -> str: ...
```

```python
ingestion_output = {
    "paragraph_index": dict,
    "appendix_index": dict,
    "traversal_plan": list[dict],
}
```

**Гарантии контрактов:**
- Любой элемент структуры приложения должен иметь `legal_ref`.
- Фазы не пишут в граф напрямую, только через `GraphOrchestrator`.
- Ошибки распознавания отдельных элементов не должны падать весь pipeline run.

## Условия выполнения

- Работать и запускать проверки только в виртуальном окружении проекта (`.venv`).
- Использовать существующий `.env` для переменных окружения (в этой задаче LLM-вызовы не обязательны, но окружение должно быть корректно подхвачено).
- Для LangGraph-интеграции в следующих задачах использовать актуальную документацию через MCP `user-docs-langchain`.

## Существующий код для reference

- `02_src/reg_graph/phases/ingestion.py` - текущая заглушка ingestion.
- `02_src/reg_graph/phases/appendix.py` - текущая заглушка appendix extraction.
- `02_src/reg_graph/graph_orchestrator.py` - оркестратор узлов/рёбер.
- `02_src/reg_graph/cli.py` - сборка фаз и запуск пайплайна.

## Артефакт выполнения от Developer

После реализации создать:
- `01_tasks/002_appendix_structure/implementation_01.md`

В отчете указать:
- какие файлы изменены/созданы;
- как выполнен smoke-прогон в venv;
- какой малый вход использован;
- какие ограничения остались до полного прогона по всему документу.
