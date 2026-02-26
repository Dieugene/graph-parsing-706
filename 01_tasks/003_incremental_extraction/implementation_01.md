# Отчет о реализации: Incremental extraction + lifecycle pending_refs

## Что реализовано

Реализована рабочая extraction-фаза на реальном LLM через `langchain-openai` и orchestration через LangGraph (`StateGraph`, `START`, `END`, `compile`, `invoke`).  
Stub extraction заменен на реальный pipeline-шаг с формированием контрактного `extraction_output`, добавлением узлов/рёбер в оркестратор и передачей `pending_refs` в `ReferenceResolverPhase`.

## Файлы

**Измененные:**
- `02_src/reg_graph/phases/extraction.py` - реальный extraction через LangGraph + `ChatOpenAI`, загрузка `.env`, нормализация LLM-выхода, запись в orchestrator.
- `02_src/reg_graph/phases/reference_resolver.py` - реализован conservative resolver `pending_refs` с попыткой матчинга к `document_section/document_field/document` и формированием `resolved/unresolved`.
- `02_src/reg_graph/graph_orchestrator.py` - добавлен API `replace_pending_refs` для обновления остатка нерезолвленных ссылок после resolver-прохода.
- `02_src/reg_graph/cli.py` - подключена новая extraction-фаза и добавлены отчеты `extraction_report`/`resolver_report` в meta-артефакт.
- `02_src/reg_graph/phases/__init__.py` - экспорт `IncrementalKnowledgeExtractionPhase` вместо stub-класса.

## Особенности реализации

### LangGraph orchestration extraction
**Причина:** AC требует использование LangGraph Python API.  
**Решение:** Extraction реализован как граф из узлов `prepare_windows -> extract_with_llm -> parse_outputs` с `StateGraph(...).compile().invoke(...)`.

### Реальный LLM без моков
**Причина:** AC требует только реальный вызов LLM через `.env`.  
**Решение:** Используется `ChatOpenAI` с `OPENAI_API_KEY` и `OPENAI_BASE_URL` из `.env` (через `python-dotenv`), без mock-ответов.

### Lifecycle pending_refs
**Причина:** Нужно показать обработку ссылок после extraction.  
**Решение:** Extraction добавляет `pending_refs`, resolver пытается их связать с существующими узлами и заменяет список `pending_refs` на остаток нерезолвленных.

## Smoke-прогон

Команда (из корня проекта, через `.venv`):

```powershell
.\.venv\Scripts\python.exe .\02_src\run_pipeline.py --input-path .\03_data\02_appendix_structure_smoke\mini_appendix.docx --output-path .\03_data\02_appendix_structure_smoke\graph_artifact_incremental.json
```

Наблюдаемые результаты:
- CLI завершился успешно (exit code 0), артефакт создан: `03_data/02_appendix_structure_smoke/graph_artifact_incremental.json`
- Счетчики CLI: `nodes=16`, `edges=17`, `pending_refs=0`, `fz_questions=0`
- Подтверждение реального LLM вызова (в `meta.extraction_report.llm_calls[0]`):
  - `model: gpt-4.1-mini-2025-04-14`
  - `finish_reason: stop`
  - `token_usage.total_tokens: 1401`
- Подтверждение обработки `pending_refs` (в `meta.resolver_report.summary`):
  - `input_count: 1`
  - `resolved_count: 1`
  - `unresolved_count: 0`
- Подтверждение изменения графа после resolver:
  - в `edges` добавлено ребро типа `REFERENCES` с `resolver=reference_resolver`.

## Известные проблемы

- Для полного документа возможны вариации качества JSON-структуры ответа LLM; сейчас включен conservative fallback-парсинг.
- Текущий matcher resolver сделан базово (token overlap) и может требовать усиления эвристик на полном корпусе 706-П.
- Нет batch/async-оптимизации окон extraction; на полном прогоне ожидается рост latency и стоимости токенов.
