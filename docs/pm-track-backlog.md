# Беклог улучшений PM-трека qtim

Дата: 2026-07-02
Статус: Draft — приоритизация ICE, оценки Ease не grounded (см. «Допущения»)
База: плагин v2.2.0 (конвейер `$qtim-feature`: intake -> PRD -> декомпозиция -> оценка -> план -> handoff)

> Эксперимент 2026-10-14: в `experiment/qtim-feature-spec` прежние full/fast
> заменены одной spec, обязательным независимым ревью и одним approval.
> Беклог ниже сохраняет историческую приоритизацию; текущий контракт —
> [feature-pipeline](../plugins/qtim/reference/feature-pipeline.md).

> Обновление 2026-07-02, v2.3.0: добавлен `$qtim-product-onboard` — продуктовая память из кода (разделы/акторы/словарь/аналитика) + глобальный инжест материалов ПМа из `docs/product-context/`. Это фундамент для #6 (context-pack): глобальный инжест реализован, per-feature `docs/features/<slug>/context/` остаётся открытым. Привязка метрик PRD к реальным событиям (`memory/product-metrics.md`) частично двигает и #12.

> Обновление 2026-07-06, v2.6.0 (порт Claude-версии 1.8.0): intake стал итеративным интервью, фазы плана сортируются по неопределённости, реализация фиксирует отклонения от `plan.md` в «Истории изменений». Последнее даёт сырьё для #10 (план-факт калибровка): факт отклонений теперь записывается, остаётся построить над ним лог оценок.

> Обновление 2026-07-21, v2.9.0: #2 реализован как fast-path `feature-brief.md` для S/M одной фазы без развилок; #11 частично закрыт универсальным `$qtim-prototype` для терминальных и UI-развилок, но автоматическая генерация прототипа непосредственно из PRD остаётся открытой.

Документ создан по итогам ресерча (конкуренты + боли ПМов) для продолжения работы в следующих сессиях: выбрать элемент волны Now и провести его через `$qtim-feature` или реализовать напрямую.

---

## Рамка и ключевые выводы ресерча

**Тезис позиционирования: усиливать привязку к коду, а не догонять генераторы документов.**
Главный дифференциатор qtim — groundedness по реальной кодовой базе — это ровно то «белое пятно», которое ресерч нашёл у всей категории. Ни один из конкурентов (ChatPRD, Zeda, BuildBetter, Notion AI, официальный PM-плагин Anthropic, ccpm, spec-kit, BMAD) не читает кодовую базу для PRD и оценок, не сверяет спеку с фактическим кодом после релиза и не даёт grounded-оценок сложности. Рынок шаблонов/генерации документов уже занят (ChatPRD: 100k+ пользователей), standalone PRD-редакторы умирают (Delibr закрывается 2026-08-31).

**Боли ПМов (данные):**

- Топ делегируемых AI задач: черновики документов — 73% ПМов, суммаризация/статусы — 52%, синтез ресерча, stakeholder-коммуникации — 33% ([Microsoft, 885 ПМов](https://arxiv.org/html/2510.02504v1); [Productboard, 379 продактов](https://www.productboard.com/blog/ai-in-product-management-report/)).
- Барьер №1 — недоверие к качеству вывода AI (47%); «accountability нельзя делегировать» ([Microsoft/arXiv](https://arxiv.org/html/2510.02504v1)).
- Главная критика AI-PRD: «многословные документы ни о чём», потому что генерируются из пустого промпта без продуктового контекста ([Aakash Gupta](https://www.news.aakashg.com/p/ai-prd)).
- Главная критика spec-driven инструментов (Kiro, spec-kit): один жёсткий workflow, overhead на мелких задачах, spec drift ([Martin Fowler](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html), [Thoughtworks](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)).
- Барьер нетехнических ПМов в CLI-агентах: «потолок сложности», нужен safe read-only режим исследования кодовой базы ([Builder.io](https://www.builder.io/blog/claude-code-for-product-managers)).

**Белые пятна экосистемы (нет ни у кого):** сверка PRD с фактическим кодом после релиза; grounded-оценки по архитектуре/истории коммитов; двусторонняя синхронизация «спека в репо ↔ трекер»; portfolio-уровень; замыкание цикла «гипотеза -> метрики -> результат»; калибровка оценок как дисциплина.

---

## Приоритизация

Фреймворк: **ICE** (Impact + Confidence + Ease, каждый 1–10). Цель приоритизации: ценность PM-трека для ПМ/аналитика = замкнуть жизненный цикл фичи вокруг кода (сейчас конвейер обрывается на handoff) + снизить порог входа.

| # | Улучшение | I | C | E | ICE | Волна |
|---|---|---|---|---|---|---|
| 1 | Feasibility-режим «спроси кодовую базу» | 8 | 8 | 9 | 25 | Now |
| 2 | Лёгкий режим конвейера (feature-lite) | 8 | 9 | 8 | 25 | Done (2.9.0) |
| 3 | Приёмка релиза: PRD vs фактический diff | 9 | 8 | 6 | 23 | Now |
| 4 | Release notes / статус-апдейт из «требование -> коммиты» | 7 | 8 | 8 | 23 | Next |
| 5 | PRD-critique («CPO-review» по коду) | 6 | 8 | 9 | 23 | Next |
| 6 | Context-pack: evidence-инжест перед PRD | 8 | 7 | 7 | 22 | Next |
| 7 | Portfolio-обзор по всем фичам | 6 | 8 | 8 | 22 | Next |
| 8 | Acceptance-пакет: UAT-сценарии из плана | 8 | 7 | 6 | 21 | Next |
| 9 | Экспорт декомпозиции в трекер (MCP) | 8 | 7 | 5 | 20 | Later |
| 10 | Калибровка оценок (план-факт лог) | 6 | 6 | 6 | 18 | Later |
| 11 | Прототип из PRD (throwaway-ветка) | 8 | 6 | 4 | 18 | Later (частично) |
| 12 | Пост-релизный metrics loop | 8 | 5 | 4 | 17 | Later |

---

## Now — следующий релиз

### 1. Feasibility-режим «спроси кодовую базу» (S/M)

Отдельный вход для ПМа без запуска конвейера: «как это сейчас устроено», «что сломается, если», «насколько это дорого» — read-only consult через architect/explorer, ответ на языке продукта.

- Evidence: safe codebase exploration — ключевой кейс нетехнических пользователей Claude Code ([Builder.io](https://www.builder.io/blog/claude-code-for-product-managers)).
- Реализация: consult-механика уже есть в Stage 3 `$qtim-feature` — вынести в самостоятельный режим (`$qtim-feature --consult` или отдельный skill).
- Ценность: расширяет ежедневную полезность — сейчас ПМ открывает qtim только с готовой хотелкой.

### 2. Лёгкий режим конвейера / feature-lite (M)

**Реализовано в 2.9.0:** после Intake qtim предлагает fast-path для S/M одной фазы без Fork Test triggers. `feature-brief.md` объединяет PRD-lite, grounded work items, оценку, gates и handoff; вместо стадий 2-5 — один checkpoint.

Для мелких фич: intake -> мини-спека (PRD + декомпозиция + оценка в одном документе) -> handoff. После общего Intake стадии 2-5 заменяет один checkpoint brief: всего два для fast-path против четырёх у текущего полного трека.

- Evidence: главная критика Kiro/spec-kit — жёсткий многостадийный workflow заставляет обходить инструмент на мелочах ([Fowler](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html), [Thoughtworks](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)).
- Риск бездействия: без лёгкого режима конвейер используется только для эпиков, привычка не формируется.

### 3. Приёмка релиза: PRD vs фактический diff (M)

После Done — команда «сверь»: product-агент + dev-consult сопоставляют acceptance criteria из `prd.md` с merged-кодом. Отчёт: покрыто / дрейфнуло / недоделано.

- Evidence: spec drift — известная боль SDD-инструментов; «accountability нельзя делегировать» — главное возражение ПМов против AI ([Microsoft/arXiv](https://arxiv.org/html/2510.02504v1)).
- Дифференциация: самое ценное белое пятно — никто на рынке этого не делает, а у qtim обе стороны уравнения в одном репозитории (спека в `docs/features/` + код).

## Next

### 4. Release notes / статус-апдейт (S/M)

`$qtim-release-notes` и статус для стейкхолдеров из цепочки «work item -> коммиты -> статус», а не из голых коммитов. Статусы и суммаризация — задачи №2 и №6 в топе делегируемых AI (52% и 33% ПМов, [Microsoft/arXiv](https://arxiv.org/html/2510.02504v1)); связка с требованиями — дифференциатор.

### 5. PRD-critique (S)

Опциональная стадия после PRD: product-агент + architect критикуют документ — пробелы в целях, отсутствие non-goals, непроверяемые метрики, конфликты с инвариантами charter. «CPO-review» — киллер-фича ChatPRD ([chatprd.ai](https://www.chatprd.ai/product/features)), но их критика слепа к коду. Реализация — промпт-паттерн, почти бесплатно.

### 6. Context-pack: evidence-инжест перед PRD (M)

Конвенция `docs/features/<slug>/context/`: ПМ складывает интервью, тикеты, выгрузки метрик; на intake product-агент синтезирует их в evidence. Закрывает критику «PRD из пустого промпта» ([Aakash Gupta](https://www.news.aakashg.com/p/ai-prd)). PRD с обоснованием «код + пользовательские данные» не даёт никто: ChatPRD видит только промпт, BuildBetter — только звонки.

### 7. Portfolio-обзор (S)

`$qtim-portfolio`: агрегировать шапки всех `docs/features/*` в сводку — статусы, фазы, что в работе, что застряло. Portfolio-уровень отсутствует во всей экосистеме; данные уже структурированы — почти чистая агрегация.

### 8. Acceptance-пакет: UAT-сценарии из плана (M)

На стадии Plan дополнительно генерировать UAT-сценарии, привязанные к реальным endpoint'ам и экранам (dev-consult уже знает файлы). ~90% организаций внедряют GenAI в QA ([testdevlab](https://www.testdevlab.com/blog/a-2025-guide-to-user-acceptance-testing)); NL-UAT из фактического кода не делает никто. Связывается с #3 — приёмка получает готовый чеклист.

## Later

### 9. Экспорт декомпозиции в трекер через MCP (L)

Work items из `decomposition.md` -> тикеты в Яндекс Трекер / Jira / Linear. Сначала one-way экспорт, обратное чтение статусов — второй этап. Двусторонней синхронизации «спека в репо ↔ трекер» нет ни у кого, но есть зависимость от MCP-окружения пользователя. Для команд с Яндекс Трекером приоритет может подняться до Next.

### 10. Калибровка оценок: план-факт лог (M)

`memory/estimates-log.md`: после Done фиксировать оценку vs фактический объём (по git log), использовать как reference class для будущих оценок — конвейер требует reference class, но сейчас ему неоткуда браться. «Оценки как дисциплина» — пробел всей экосистемы.

### 11. Прототип из PRD (M/L)

**Частично реализовано в 2.9.0:** `$qtim-prototype` создаёт throwaway terminal/UI prototype для конкретной design-развилки и встроен в architect/intake. Отдельный автоматический переход «утверждённый PRD -> прототип» пока не реализован.

Кликабельный прототип силами dev-агента в throwaway-ветке как опция после PRD. Быстрорастущий кейс — время ПМов на мокапы упало вдвое ([638 practitioner voices](https://medium.com/@haberlah/what-638-practitioner-voices-reveal-about-pms-ai-transformation-7d2fd16be10d)). Конфликтует с принципом «PM-трек не пишет production code» — оформить как явно не-production артефакт.

### 12. Пост-релизный metrics loop (L)

PRD фиксирует metric-план и события трекинга (по реальному аналитическому коду в репо); после релиза — «проверь гипотезу». Белое пятно у всех ([Userpilot](https://userpilot.com/blog/ai-product-analytics/)), но Confidence низкий: требует доступа к аналитике проекта.

---

## Осознанно не в беклоге

- **Библиотека шаблонов PRD и multi-doc генерация** — коммодити, ChatPRD и Notion уже выиграли эту гонку; qtim конкурирует groundedness'ом.
- **Собственный синтез звонков/транскриптов** — территория BuildBetter/Zeda; context-pack (#6) закрывает потребность приёмом готовых материалов.
- **Web-UI / коллаборация** — против природы repo-native инструмента; версионирование уже даёт git.

## Допущения

- Оценки Ease — экспертная прикидка по знанию кодовой базы плагина, не grounded-оценка dev-агентов. Рекомендация: прогнать элементы волны Now через собственный `$qtim-feature` перед реализацией.
- Impact оценён против цели «ценность для ПМа + дифференциация» без данных о реальных пользователях плагина; пересмотреть после первых внедрений.
- Пробел ресерча: детальный разбор AI-фич Jira Rovo / Linear / Productboard и глубокое погружение в Kiro покрыты частично (из смежных отчётов); на состав беклога не влияет.

## Источники ресерча

- [Microsoft: исследование 885 ПМов (arXiv)](https://arxiv.org/html/2510.02504v1)
- [Productboard: The New Reality of AI in Product Management](https://www.productboard.com/blog/ai-in-product-management-report/)
- [Lenny's Newsletter: опрос 1750 специалистов](https://www.lennysnewsletter.com/p/ai-tools-are-overdelivering-results-c08)
- [Aakash Gupta: AI PRD](https://www.news.aakashg.com/p/ai-prd)
- [Builder.io: Claude Code for Product Managers](https://www.builder.io/blog/claude-code-for-product-managers)
- [Sachin Rekhi: Claude Code for PMs](https://www.sachinrekhi.com/p/claude-code-for-product-managers)
- [Martin Fowler: SDD tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [Thoughtworks: Spec-driven development](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [ChatPRD](https://www.chatprd.ai/product/features) · [ccpm](https://github.com/automazeio/ccpm) · [spec-kit](https://github.com/github/spec-kit) · [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) · [Anthropic product-management plugin](https://github.com/anthropics/knowledge-work-plugins/tree/main/product-management) · [claude-task-master](https://github.com/eyaltoledano/claude-task-master) · [BuildBetter](https://www.buildbetter.ai/) · [Zeda.io](https://zeda.io/)
