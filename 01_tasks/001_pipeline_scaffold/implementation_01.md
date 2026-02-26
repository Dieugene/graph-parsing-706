# Отчет о реализации: Python core scaffold (pipeline, LPG, orchestrator, CLI)

## Что реализовано

Реализован каркас Python-пакета в `02_src/` для Iteration 1: модели LPG, оркестратор графа, последовательный раннер фаз, заглушечные фазы и CLI-запуск с записью JSON-артефакта в `03_data/`.

## Файлы

**Новые:**
- `02_src/reg_graph/__init__.py` - экспорт базовых сущностей пакета.
- `02_src/reg_graph/graph_model.py` - модели `GraphNode`, `GraphEdge`, `GraphState`.
- `02_src/reg_graph/graph_orchestrator.py` - `GraphOrchestrator` c `add_or_update_node`, `add_edge`, `add_pending_ref`, `to_json`.
- `02_src/reg_graph/pipeline.py` - `PipelinePhase` и `PipelineRunner` для последовательного исполнения фаз.
- `02_src/reg_graph/phases/__init__.py` - реестр заглушечных фаз.
- `02_src/reg_graph/phases/ingestion.py` - stub `DocumentIngestionPhase`.
- `02_src/reg_graph/phases/appendix.py` - stub `AppendixStructureExtractorPhase`.
- `02_src/reg_graph/phases/extraction.py` - stub `IncrementalKnowledgeExtractionStubPhase` с демо-узлами/рёбрами/refs/questions.
- `02_src/reg_graph/phases/reference_resolver.py` - stub `ReferenceResolverPhase`.
- `02_src/reg_graph/phases/validation.py` - stub `ValidationAndQAPhase`.
- `02_src/reg_graph/cli.py` - сборка пайплайна, запуск и сохранение артефакта.
- `02_src/run_pipeline.py` - CLI-скрипт запуска.
- `03_data/01_pipeline_scaffold/graph_artifact.json` - артефакт smoke-запуска.

## Особенности реализации

### Детерминированные ID в оркестраторе
**Причина:** Нужен стабильный каркас ID-менеджмента уже на первом шаге без внешних зависимостей.  
**Решение:** ID узлов и рёбер формируются из сигнатуры через SHA-1 префикс (`node_*`, `edge_*`), при повторном upsert/добавлении обновляются свойства существующих сущностей.

### Заглушки вместо интеграций
**Причина:** По task_brief в Iteration 1 запрещены внешние интеграции и отдельный парсинг ФЗ.  
**Решение:** Фазы ingestion/extraction/resolver/validation работают на фиксированных данных и формируют `pending_refs` + `fz_questions` как сервисные артефакты.

## Smoke-check

Команда:

```bash
python 02_src/run_pipeline.py
```

Результат:
- `Pipeline scaffold artifact saved to: D:\_workspace\graph-parsing-706\03_data\01_pipeline_scaffold\graph_artifact.json`
- `Counts: nodes=4 edges=2 pending_refs=1 fz_questions=1`
- В JSON присутствуют секции `nodes`, `edges`, `pending_refs`, `fz_questions`.

## Моки/заглушки для замены в следующих итерациях

- `02_src/reg_graph/phases/ingestion.py:DocumentIngestionPhase.run` — фиксированный `ingestion_output`; заменить на реальный DOCX parser/индексацию.
- `02_src/reg_graph/phases/extraction.py:IncrementalKnowledgeExtractionStubPhase._build_stub_output` — демо extraction-пакет; заменить на фактическое извлечение по окнам текста.
- `02_src/reg_graph/phases/reference_resolver.py:ReferenceResolverPhase.run` — no-op resolver; заменить на реальный алгоритм связывания `pending_refs`.
- `02_src/reg_graph/phases/validation.py:ValidationAndQAPhase.run` — базовая статистика; заменить на rule-based QA и отчеты аномалий.

## Известные проблемы

- На данном этапе нет реального разбора исходного документа и внешних ФЗ (только каркас/заглушки по ТЗ).
