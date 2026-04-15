# Repo Architecture Audit

Дата: 2026-04-15

## Краткий вывод

Проект уже не "набор скриптов". В нём есть реальная архитектурная идея:

- `control_plane`
- модульные агенты
- контракты и approvals
- state/output separation как концепция
- несколько независимых пайплайнов вокруг discovery, intelligence и outreach

Проблема не в отсутствии архитектуры. Проблема в том, что в одном репозитории сейчас живут **две разные модели одновременно**:

1. `task-driven control plane` вокруг Instagram discovery / brand intelligence / conversation
2. `script-driven research pipeline` вокруг company contacts enrichment / The Blueprint / ad-hoc отчетов

Из-за этого репозиторий выглядит как смесь:

- importable Python package
- операционного хранилища state/tasks/decisions
- артефактного хранилища output/playwright/screenshots
- ручных входных файлов
- временных исследований и one-off scripts

Это делает проект тяжёлым для чтения, хрупким для изменений и дорогим в поддержке.

---

## Что в проекте уже хорошо

Это не нужно ломать, это нужно сохранить:

1. `automation/control_plane/` уже выглядит как отдельный слой оркестрации.
2. `automation/agents/contracts/*.yaml` даёт формальные handoff-модели.
3. Модульная идея `brand_intelligence -> brand_arbiter -> outreach_planning -> conversation -> validation` правильная.
4. У большинства agent-модулей есть `README.md`, `job.yaml`, `state.py`, `worker.py`.
5. Разделение на `inputs / output / knowledge / state` задумано правильно, даже если реализовано непоследовательно.

---

## Главные архитектурные проблемы

## 1. Код, runtime-state и артефакты смешаны в одном рабочем пространстве

Сейчас репозиторий одновременно хранит:

- код в `automation/` и `scripts/`
- входные данные в `inputs/`
- операционные state-файлы в `automation/state/`
- lifecycle task JSON в `automation/tasks/`
- approvals в `automation/decisions/`
- тяжелые outputs в `output/`

Это ломает границу между:

- source code
- runtime data
- generated artifacts

Практический эффект:

- git history засоряется артефактами
- source of truth становится неочевидным
- изменения в коде и результаты прогонов постоянно перемешаны

## 2. Слишком много entrypoints без единой карты продукта

На текущий момент:

- `130` Python-файлов
- `34` отдельных CLI-скрипта в `scripts/`
- только `3` тестовых файла, и это скорее smoke/manual scripts, а не test suite

Проблема не в числе скриптов как таковом, а в том, что они не организованы как понятные product surfaces.

Например сейчас рядом живут:

- `run_supervisor.py`
- `run_company_enrichment.py`
- `run_theblueprint_career_parser.py`
- `build_theblueprint_people_targets.py`
- `build_theblueprint_master_report.py`
- `send_mailru_batch.py`
- `send_instagram_dm_batch.py`

Для нового человека непонятно:

- какие скрипты продовые
- какие сервисные
- какие one-off
- какие deprecated

## 3. В проекте одновременно две разные архитектуры

### Архитектура A: control-plane

Она описана в `README.md` и `AUTOMATION.md`.

Сильные стороны:

- supervisor
- approvals
- task routing
- profile leasing
- logical agents

### Архитектура B: research/report scripts

Она живёт вокруг `company_contacts_enrichment` и особенно The Blueprint пайплайна.

Сильные стороны:

- быстрый delivery
- stage-based enrichment
- понятные outputs

Слабые стороны:

- обходит control-plane
- имеет собственные runner scripts
- имеет собственные conventions
- плохо интегрирована с общей task model

В итоге у проекта нет одной "операционной оси". Есть две.

## 4. Границы модулей непоследовательны

Некоторые модули оформлены как полноценные agent-модули:

- `brand_intelligence`
- `conversation`
- `feedback_validation`
- `instagram_brand_search`

У них есть понятный shape:

- `README.md`
- `job.yaml`
- `state.py`
- `worker.py`
- иногда `runners/`

Но `company_contacts_enrichment` устроен иначе:

- много stage-specific файлов
- отдельные reports/builders
- source parsers
- собственный `worker.py`
- набор ad-hoc runner scripts снаружи

Это говорит о том, что модуль решает уже не одну задачу, а целое приложение внутри приложения.

## 5. Есть legacy / orphaned код

Это прямой structural smell:

- `automation/state.py` до сих пор содержит `GenaiproState`
- `automation/modules/genai/` фактически пустой и состоит из `__pycache__`
- `archive/genaipro_legacy/` уже существует

То есть legacy не изолирован до конца. Он продолжает торчать в активной структуре.

## 6. Общие utility-слои продублированы

Примеры:

- UTF-8 / mojibake repair живёт и в `text_utils.py`, и отдельно внутри `scripts/run_company_enrichment.py`
- state persistence сделан как минимум в нескольких стилях
- path conventions зашиты строками по всему проекту
- output/state/input paths часто объявлены прямо в скриптах

Это затрудняет:

- тестирование
- refactor
- перенос папок
- упаковку в один CLI

## 7. Репозиторий слишком output-heavy

Сейчас только в `output/`:

- `1000` файлов
- около `60.5 MB`

При этом часть `output/` коммитится, часть игнорируется, часть selectively unignored.

Это означает, что output сейчас используется и как:

- артефакт прогона
- кэш
- результат работы
- иногда почти как база данных

Это опасная роль для одной директории.

## 8. Нет нормального packaging/tooling слоя

Сейчас:

- нет `pyproject.toml`
- нет lockfile
- нет pytest suite
- нет ruff/black/mypy config
- `requirements.txt` содержит только `playwright` и `PyYAML`

Это означает, что фактическая среда проекта богаче, чем формально описанная. Для нового запуска это риск.

---

## Как я бы описал проект продуктово

На самом деле здесь не один проект, а три продукта в одном repo:

1. `Instagram Discovery`
   Задача: искать бренды и кандидатов через Instagram/AdsPower/Playwright.

2. `Company Research`
   Задача: строить company cards, contact routes, The Blueprint shortlists, people targets, resolver outputs.

3. `Outreach Operations`
   Задача: planning -> approval -> draft -> send -> audit.

Сейчас эти три поверхности перемешаны в папках и скриптах.

Их надо сделать явными.

---

## Целевая структура

Важно: я **не рекомендую** сразу делать большой rename в `src/autoskill`. Это слишком дорогой шаг на текущей стадии.

Сначала лучше привести проект к чистой внутренней структуре, сохранив пакет `automation/`.

### Предлагаемая структура верхнего уровня

```text
automation/             # только importable code
configs/                # yaml/json конфиги, registry, jobs, routing
docs/                   # архитектура, runbooks, ADR
inputs/                 # только человеко-редактируемые входы
runtime/                # state/tasks/decisions, gitignored
artifacts/              # outputs/reports/screenshots, gitignored
legacy/                 # архив старых пайплайнов
scripts/                # тонкие CLI wrappers, не бизнес-логика
tests/                  # unit + integration + smoke
```

### Внутри `automation/`

```text
automation/
  core/
    config/
    paths/
    state/
    artifacts/
    text/
    logging/

  infra/
    browser/
    adspower/
    web/
    mail/

  control_plane/
    ...

  apps/
    instagram_discovery/
    company_research/
    outreach_ops/

  modules/
    brand_intelligence/
    brand_arbiter/
    outreach_planning/
    conversation/
    feedback_validation/
```

### Что куда переезжает

#### `automation/config.py`, `artifacts.py`, `state.py`

Нужно разнести:

- `automation/core/config.py`
- `automation/core/artifacts.py`
- `automation/core/state.py`

`automation/state.py` с `GenaiproState` надо либо удалить, либо перенести в `legacy/`.

#### `company_contacts_enrichment`

Это уже не "модуль", а mini-app.

Его лучше привести к форме:

```text
automation/apps/company_research/
  pipelines/
    company_enrichment/
    theblueprint/
  sources/
  reports/
  models/
  services/
```

То есть:

- `theblueprint_shortlist.py`
- `theblueprint_people_targets.py`
- `theblueprint_route_resolver.py`
- `theblueprint_master_report.py`

должны стать частями одного приложения `company_research`, а не висеть рядом с generic `worker.py`.

#### `scripts/`

Нужно оставить только thin wrappers.

Например:

```text
scripts/
  run_supervisor.py
  run_discovery.py
  run_company_research.py
  run_outreach_ops.py
  admin/
  migration/
  oneoff/
```

Сейчас `scripts/` надо минимум разбить на:

- `scripts/run/`
- `scripts/admin/`
- `scripts/reporting/`
- `scripts/oneoff/`

#### `output/`

Нужно переименовать концептуально в `artifacts/`.

Внутри разделить:

```text
artifacts/
  reports/
  exports/
  browser_runs/
  supervisor/
  company_research/
  discovery/
```

Папка `output/playwright/` должна быть чисто runtime-artifact и точно не участвовать в source-layout.

#### `automation/tasks`, `automation/decisions`, `automation/state`

Это не код. Это runtime.

Их лучше вынести в:

```text
runtime/
  state/
  tasks/
  decisions/
```

Так станет визуально очевидно, что это не importable package.

---

## Рекомендованный план рефактора

## Phase 0. Hygiene без ломки логики

Это можно делать сразу.

1. Добавить `docs/` как место для архитектурных документов.
2. Удалить/перенести orphaned `genai` из активной структуры.
3. Перенести `automation/state.py` legacy-код в `legacy/`.
4. Почистить `__pycache__` из репозитория и убедиться, что они не трекаются.
5. Разделить `scripts/` на подкаталоги хотя бы логически.
6. Перестать коммитить runtime-heavy outputs по умолчанию.

## Phase 1. Ввести явные product surfaces

Нужно назвать и закрепить три приложения:

- `instagram_discovery`
- `company_research`
- `outreach_ops`

И для каждого сделать один нормальный основной CLI.

Например:

```powershell
python scripts/run/discovery.py
python scripts/run/company_research.py
python scripts/run/outreach_ops.py
python scripts/run/supervisor.py
```

Все остальные команды становятся subcommands или admin scripts.

## Phase 2. Нормализовать package layout

Цель:

- всё importable остаётся внутри `automation/`
- всё runtime выносится из `automation/`
- всё generated выносится из `output/` в `artifacts/`

То есть проект перестаёт хранить код и данные в одной namespace-структуре.

## Phase 3. Нормализовать общие слои

Нужно централизовать:

- `paths`
- `state json persistence`
- `text encoding / utf8 / mojibake repair`
- `artifact path conventions`
- `slug / brand normalization`

Сейчас эти куски живут в нескольких местах и их надо собрать в `automation/core/`.

## Phase 4. Свести The Blueprint и company enrichment в единое приложение

Вместо нескольких build scripts и stage-файлов сделать один app-layer:

```text
company_research
  parse_source
  reduce_shortlist
  enrich_people_targets
  resolve_routes
  build_report
```

С единым CLI и единым config.

## Phase 5. Нормальный test layer

Сначала не надо покрывать всё.

Достаточно:

1. `tests/unit/test_text_utils.py`
2. `tests/unit/test_theblueprint_shortlist.py`
3. `tests/unit/test_route_resolver_filters.py`
4. `tests/unit/test_brand_slug_normalization.py`
5. `tests/smoke/test_supervisor_imports.py`

Это уже резко снизит страх перед рефактором.

---

## Что я бы сделал первым делом

Если выбирать только 5 шагов:

1. Вынес бы runtime из `automation/` в `runtime/`.
2. Вынес бы `output/` концептуально в `artifacts/` и перестал бы смешивать его с source repo.
3. Разбил бы `scripts/` на `run/admin/reporting/oneoff`.
4. Оформил бы `company_contacts_enrichment` как `company_research app`, а не как набор stage-файлов рядом с generic worker.
5. Добавил бы `pyproject.toml` + `tests/` + базовый `ruff/pytest`.

---

## Какой рефактор НЕ надо делать сейчас

Не надо начинать с:

- тотального rename всех импортов
- миграции на новую супер-абстракцию
- переписывания control plane
- попытки унифицировать всё через одну магическую base class

Это сломает скорость.

Правильный путь:

- сначала разложить проект по границам
- потом унифицировать общие слои
- потом уже решать, нужен ли rename пакета

---

## Практический целевой результат

Через один аккуратный рефактор проект должен читаться так:

1. Есть понятные приложения:
   - discovery
   - company research
   - outreach ops

2. Есть понятные слои:
   - core
   - infra
   - control plane
   - domain modules

3. Есть понятные директории данных:
   - inputs
   - runtime
   - artifacts
   - docs

4. Есть 4-6 основных CLI входов вместо 34 равноправных скриптов.

5. Legacy не торчит в active code.

6. Любой новый человек понимает:
   - что запускать
   - где source of truth
   - где код
   - где runtime
   - где мусор

