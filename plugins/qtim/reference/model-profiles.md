# Модельные профили qtim для Codex

Эта политика разделяет оркестрацию и работу ролей. Custom agents, которые `$qtim-setup` копирует в `.codex/agents/*.toml`, получают явные GPT-6 пары. Main thread остаётся team-lead и для qtim workflow должен быть запущен на `gpt-6-astra` + `ultra`; плагин не меняет профиль уже открытого task скрыто.

## Профили по умолчанию

| Роль | Model / reasoning | Почему |
|---|---|---|
| team-lead (main thread) | `gpt-6-astra` + `ultra` | оркестрация, синтез и proactive delegation внутри явно разрешённого qtim workflow |
| architect | `gpt-6-astra` + `xhigh` | one-way doors, ADR и защита инвариантов требуют глубокого reasoning |
| database | `gpt-6-sol` + `high` | security/data-integrity требуют качественной проверки, но bounded scope не оправдывает xhigh по умолчанию |
| frontend | `gpt-6-sol` + `high` | production UI, интеграционные и поведенческие развилки |
| reviewer | `gpt-6-astra` + `xhigh` | строгий финальный гейт не должен зависеть от профиля основной сессии |
| product | `gpt-6-sol` + `high` | intake, trade-offs и grounded synthesis |
| testing | `gpt-6-luna` + `medium` | bounded QA-прогоны и сбор evidence выгоднее держать на явном более дешёвом профиле |
| explorer (built-in, без TOML) | `gpt-6-luna` + `medium` | ясный read-heavy поиск и первичная классификация; main thread передаёт пару при spawn |
| ADR adversary (ephemeral) | `gpt-6-astra` + `xhigh`; `max` для необратимого + инвариант | независимый read-only stress-test без истории текущего task |

Все постоянные роли pinned к семейству GPT-6 точным variant slug. Это отделяет модель, удобную для оркестрации, от модели, нужной конкретной роли. В Codex нет значения `model = "inherit"`; half-pair запрещена.

## Root reasoning и Ultra

- qtim не может переключить модель/reasoning уже открытого task. Перед `$qtim-feature`, `$qtim-team-up`, `$qtim-team-lazy`, `$qtim-mission`, `$qtim-onboard` или `$qtim-product-onboard` пользователь выбирает `gpt-6-astra` + `Ultra`; если runtime показывает другой профиль, workflow останавливает fan-out и просит открыть новый task с Astra/Ultra.
- Вызов `$qtim-feature`, `$qtim-team-up`, `$qtim-team-lazy`, `$qtim-mission`, `$qtim-onboard` или `$qtim-product-onboard` — явное разрешение только на описанный skill workflow. `Ultra` не расширяет scope и не превращает любой запрос в full team-up или cross-dialog mission.
- `Ultra` закреплён за main thread, не за role TOML. Child agents не поднимают qtim-команду рекурсивно; fan-out координирует main thread.
- `Max` используется точечно только для clean-context ADR adversary, когда решение одновременно необратимо и затрагивает документированный инвариант. Fast не является qtim default.
- Direct peer-задачи `$qtim-mission` используют configured default destination
  task: coordinator не передаёт `model`/`thinking`. Lazy node lead получает
  `gpt-6-astra` + `ultra` только когда exact atomic pair явно утверждена
  пользователем в mission preview/Approved spec; это не разрешает менять direct
  peers или local role pairs.

## Явные пары и overrides

- Явный профиль всегда атомарен: `model` + `model_reasoning_effort` вместе.
- Template pair каждой роли копируй дословно. Для built-in `explorer` main thread задаёт `gpt-6-luna` + `medium` при spawn; если runtime допускает model override только без full-history fork, используй `fork_turns = "none"` и передай весь bounded context в начальном prompt. Если точный slug недоступен, не угадывай alias и не подменяй модель молча: используй `worker`/`explorer` fallback только после сообщения пользователю и оставь migration pending.
- Пользователь может pin любую роль явным catalog-supported override. `$qtim-update` показывает diff и не перезаписывает такой override молча.
- При миграции прежний qtim-default заменяй только по fingerprint конкретной upgrade section; отличающаяся pair или сохранённое inheritance считаются пользовательским override до показанного diff и подтверждения.
- Профиль роли не определяет execution depth, число агентов или обязательность review.

Актуальные model slugs и возможности сверяй с официальными страницами [Models](https://learn.chatgpt.com/docs/models) и [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), а доступность — с локальным runtime catalog.
