# Отчет о реализации: Appendix structure extraction и подграф форм

## Что реализовано

Реализована поддержка чтения реального DOCX во входной фазе через `python-docx` при передаче `--input-path`.  
Фаза `appendix` теперь строит в `GraphOrchestrator` узлы типов `document_section`, `document_field`, `field_group` и соответствующие связи, при этом для созданных узлов и рёбер сохраняется `legal_ref`.  
Поведение fallback сохранено: при отсутствии `input_path` или недоступности DOCX используется stub-выход ingestion.

## Файлы

**Новые:**
- `01_tasks/002_appendix_structure/implementation_01.md` - отчет о реализации.
- `03_data/02_appendix_structure_smoke/mini_appendix.docx` - малый вход для smoke-прогона.
- `03_data/02_appendix_structure_smoke/graph_artifact.json` - артефакт smoke-прогона.

**Измененные:**
- `02_src/reg_graph/phases/ingestion.py` - добавлен DOCX ingestion через `python-docx`, построение `appendix_index`/`paragraph_index` и fallback.
- `02_src/reg_graph/phases/appendix.py` - реализовано построение подграфа приложений (`document_section`, `field_group`, `document_field`) через API оркестратора.
- `02_src/reg_graph/graph_orchestrator.py` - добавлены методы `upsert_document_section`, `upsert_document_field`, `upsert_field_group`.
- `02_src/reg_graph/cli.py` - обновлено описание аргумента `--input-path`.

## Особенности реализации

### Fallback и DOCX ingestion в одной фазе
**Причина:** по AC нужен реальный DOCX ingestion, но также требуется сохранить деградацию без `input_path`.  
**Решение:** `DocumentIngestionPhase` сначала пытается прочитать DOCX (если путь передан), иначе возвращает прежний stub-индекс.

### Минимально-детерминированный API оркестратора для структуры приложений
**Причина:** AC требует создавать узлы структуры приложений через `GraphOrchestrator`, а не напрямую.  
**Решение:** добавлены специализированные upsert-методы для `document_section`/`document_field`/`field_group` с детерминированными natural key.

## Smoke-прогон

Запуск выполнен в venv:

`.\.venv\Scripts\python 02_src/run_pipeline.py --input-path "03_data/02_appendix_structure_smoke/mini_appendix.docx" --output-path "03_data/02_appendix_structure_smoke/graph_artifact.json"`

Результат:
- Команда завершилась с кодом `0`.
- В артефакте появились узлы:
  - `document_section` (2 шт.),
  - `field_group` (2 шт.),
  - `document_field` (3 шт.).
- У созданных узлов и связей присутствует `legal_ref` (`706-П, приложение 1`).

## Известные проблемы

- Текущая эвристика парсинга DOCX опирается на текстовые шаблоны абзацев и не извлекает структуру таблиц DOCX.
- Для полного 706-П потребуется усилить правила сегментации разделов/полей и журналирование неоднозначных элементов (`extraction_warnings`).
