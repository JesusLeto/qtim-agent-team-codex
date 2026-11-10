# Feature-pipeline qtim для Codex: одна спецификация

> Долговечный канон новой фичи: `spec.md`, этапы, тикеты, ревизии и handoff.
> Сессионную оркестрацию ведёт `$qtim-feature`; независимый review —
> [independent-review.md](independent-review.md), исполнение —
> [feature-execution.md](feature-execution.md). PM-блок charter — производная сводка.

## Контракт

Интервью → одна спецификация с независимым ревью → утверждение → handoff.
Новые планы используют последовательные этапы и тикеты: одна стадия с одним
тикетом валидна. Размер влияет на число work items, а не создаёт другой процесс.
Main thread — единственный редактор `docs/features/<slug>/spec.md` и контрактов
`tickets/Txx-<slug>.md`; product и dev-роли дают
точечные consult-выводы, reviewer — read-only findings. Production code, SQL,
тесты и будущие диффы здесь не создаются.

Источники из кода и документов агент проверяет сам. Пользователю возвращаются
невыводимые продуктовые решения и конфликты требований, а не вопросы о фактах,
эквивалентных деталях реализации или выборе ролей. Интервью завершено, когда
разрешены вопросы, меняющие scope, поведение, контракты и приёмку.

## `spec.md`

```text
# Feature: <название>
Feature: <название>
Slug: <slug>
Status: Draft | Approved | In Development | Done | Archived
Revision: <целое число, начиная с 1>
Reviewed revision: <номер | none>
Approved revision: <номер | none>
Review verdict: pending | READY_FOR_APPROVAL | CHANGES_REQUESTED | UNAVAILABLE | WAIVED
Дата: YYYY-MM-DD

## Проблема и результат
## Scope и non-goals
## Сценарии и acceptance criteria
## Принятые решения и источники
## Work items
## Gates и условия Done
## Риски, внешние зависимости и rollback
## Результат ревью
## Handoff
## История изменений
```

Если в каталоге одновременно есть spec и legacy-источники, явный выбор spec
фиксируется шапкой `Canonical: spec.md`; для spec-only эта строка необязательна.
Acceptance criteria имеют стабильные `AC-*`, решения — `D-*`, work items —
`WI-*`, этапы — `S*`, тикеты — `Txx`. ID сохраняются при перестановке очереди.
Решение содержит выбранное поведение и основание: ответ владельца,
проверенный контракт или инвариант. Кодовые факты имеют проверяемые символические
ссылки по `$qtim-kb-format`. Метрики, если нужны, опираются на существующие события;
отсутствующее событие — задача tracking, а не выдуманный факт.

`Work items` — одна таблица:

| Stage | WI / Ticket | Проверяемый результат / AC | DRI | Contributing роли/слои | Scope / файлы | Технические prerequisites | Граница review |
|---|---|---|---|---|---|---|---|
| S1 | WI-01 / T01 → `tickets/T01-slice.md` | вертикальный срез, AC-01 | одна роль | затронутые слои | repo-relative paths | входной контракт / receipt | устойчивый пакет результата |

DRI владеет главной acceptance boundary. Это единственный реестр работ; отдельный
`plan.md` и таблица фаз, пересказывающая те же items, не создаются. Каждая строка
ссылается на свой ticket file; каждый feature AC имеет owning ticket и final gate.
Все ссылки разрешаются, dependency graph ацикличен. В `Gates` задай обязательные
tickets и gate каждого этапа.

Очередь задаёт последовательность исполнения отдельно от технических prerequisites.
До старта её фиксируют в handoff, при исполнении её единственный live-источник —
ledger по feature-execution. В один момент активен только один тикет, включая
preflight, исправления и ожидание приемки. Перестановка очереди не удаляет
техническую зависимость и не разрешает пропуск stage gate.
Широкий rename/retype режется через expand-contract: новая форма рядом → миграция
call sites проверяемыми пачками → удаление старой формы. Очевидный XL разрезается
независимо от наличия оценки.

Оценка добавляется полем к work item лишь по запросу или для реального решения
об исполнителе, сроке/бюджете: S/M/L/XL + confidence + evidence + риски, без
выдуманных часов. Contributing роли оценивают только неизвестные layer slices;
DRI синтезирует интеграционный риск, main thread сводит результат. Оценка не
создаёт отдельного документа, обязательного fan-out или checkpoint.

Gates связываются с AC и риском по [intake-protocol.md](intake-protocol.md): требуемые typecheck/build/tests, browser/native
или integration evidence, контракты внешних сервисов. Done требует их реального
прохождения. Формат execution ledger, durable receipts и raw evidence — в
[feature-execution.md](feature-execution.md); требования не дублируют live status.

## Контракт тикета

Каждый `tickets/Txx-<slug>.md` содержит:

- Feature/Slug, Stage, Ticket ID, Ticket revision, Spec revision и ADR revision
  (`none`, если ADR не нужен), DRI и contributing роли;
- цель и проверяемый результат, разрешённый scope/файлы и non-goals;
- prerequisites: точные входные artifacts/receipts и их revisions/result identity;
  необходимые секции spec/ADR, правила проекта и профильную memory;
- собственные `Txx-AC*` со связью с feature `AC-*`, обязательные проверки и
  достаточный стенд с явно указанными ограничениями evidence;
- ожидаемый receipt по feature-execution и стартовый prompt отдельного чата:
  только этот тикет, read-only preflight до bounded write-go coordinator,
  граница записи, stop conditions, возврат результата и остановка.

Feasibility проверяется на доступной части системы: ранний harness вызывает
реальный проверяемый компонент. Будущий UI/backend не становится prerequisite,
если не нужен для данного AC. Harness не закрывает отдельный integration/E2E
gate; этот gate получает свой required ticket. Неизвестный обязательный вход
означает Blocked, а не фиктивное покрытие. Перед dispatch coordinator уточняет
worktree/base/dirty fingerprint и права git; worker читает только этот context
pack, нужные dependency receipts и дополнительный необходимый код, а не историю
соседей или все tickets/raw logs.

## Изменение scope и перенос обязательств

Неполный текущий scope не принимается как полный. До partial acceptance владелец
утверждает новую проверяемую границу, а coordinator ревизует затронутые контракты:
оставшиеся AC получают **названный required receiving ticket**, prerequisites,
проверки и связь с прежним scope и final feature AC. Evidence прежней ревизии
остаётся историей; PASS ей задним числом не назначается.

`Deferred` требует решения владельца, причины и того же явного переноса. Если
receiving ticket отсутствует или не принят, соответствующий final gate открыт.
Перенос может изменить очередь, но сохраняет AC coverage и технические входы;
отложенный required ticket не считается завершённым. Существенная смена scope,
AC, зависимости или gate отзывает affected approvals по правилам ревизий ниже.
Чистая перестановка очереди меняет execution plan, а не продуктовые требования.

## Ревизии и принятые решения

`Revision` меняется при существенном изменении scope, AC, решения, границы work
item/review, материальной зависимости, обязательного gate, rollback или результата
handoff. Новая версия становится `Draft`, `Review verdict: pending`; прежние
`Reviewed revision` и `Approved revision` сохраняются как история и не разрешают
новую версию. Если waiver относился к прежней ревизии, новая требует отдельного
owner decision; старое исключение не переносится.
Статус, receipt проверки, форматирование и эквивалентная техническая деталь
ревизию контракта не меняют.
Затронутый ticket contract получает новую Ticket revision и привязку к актуальным
spec/ADR; его прежняя приемка не разрешает новый scope. Остальные решения и
подтверждённо актуальное evidence сохраняются; смена attempt не меняет контракт.

Для пересмотра принятого `D-*` нужны новый подтверждённый факт, затронутое
решение и конкретное последствие. Альтернативный вкус другого агента не повод
повторять интервью. Владельцу показывается существенная дельта, остальные
решения сохраняются. Защищённые зоны, инварианты и настоящий ADR сохраняют свои
gates; approval спецификации их не отменяет.

`Результат ревью` кратко хранит reviewer/thread, рассмотренную ревизию, исходный
вердикт и findings с источниками, подтверждение/отклонение main thread, закрытие
блокеров и `Review budget: full-pass 0/1; fix-recheck 0/1` с фактическими счётчиками.
Бюджет принадлежит фиче и стабильным границам работы; новый агент, resume,
compaction и переименование ревизии его не обнуляют. Raw reports — в `.work/`.
Существенно новый scope после исчерпания бюджета требует явного решения владельца
о scope и новом бюджете. Непреодолённый подтверждённый blocker → workflow `Blocked`, spec остаётся `Draft`.

Перед approval должны быть разрешены блокирующие продуктовые вопросы и
подтверждённые findings, а reviewer завершил текущую ревизию с
`READY_FOR_APPROVAL`. `Reviewed revision = Revision` само по себе недостаточно:
`CHANGES_REQUESTED` остаётся незавершённым gate. При единственном целевом recheck
reviewer получает существенную дельту и затронутые AC/решения; если дельта требует
полного нового прохода сверх бюджета, остановись для owner decision.

Main thread связывает явное пользовательское approval с показанной ревизией и
ставит `Approved revision = Revision`, `Status: Approved`. Совмещённое
«утверждаю и запускай показанную команду» также разрешает её исполнение.
Независимый reviewer не заменяет approval владельца.

Review спецификации обязателен независимо от optional code review. Его отсутствие
не означает готовность. Исключение — явный waiver владельца после сообщения
причины и риска: сохранить `Reviewed revision: none`, `Review verdict: WAIVED`,
точную текущую ревизию/область waiver и ссылку на owner decision; никогда не
обозначать его `READY_FOR_APPROVAL` или PASS. Waiver — только explicit owner
exception, требует ручной проверки полномочий/риска перед исполнением, не
автоматический fallback. Scanner не подтверждает Done для WAIVED автоматически.
При технической недоступности без waiver ставь `UNAVAILABLE`, spec остаётся
Draft, workflow — `Blocked`.

## Handoff и resume

Handoff полностью составлен **до** review и approval. Он содержит источник
`spec.md` с ревизией, scope/AC/gates, внешние блокеры, команду реализации и блок
`Что запускать дальше` с пятью полями: `Рекомендация`, `Почему`, `Топология`,
`Команда`, `Альтернатива`.

Для нового stage/ticket плана recommendation — последовательное исполнение через
исходный feature coordinator по feature-execution: новый чат на тикет и возврат
в coordinator для проверки/приемки. Handoff фиксирует очередь, stage/final gates,
workspace/git permissions и canonical execution root до init ledger.
Planning-only заканчивается после handoff; approval spec, разрешение старта,
worker completion, проверка coordinator, owner acceptance, advance и release —
разные решения по execution reference. Рекомендация не доказывает наличие
App/state capabilities: недоступность даёт Blocked/Unavailable, без скрытой
подмены другим процессом.

Для явно выбранного standalone исполнения и действующих legacy/spec-only планов
сохраняется routing по execution topology:

- один bounded outcome без fan-out → direct;
- один outcome, несколько точечных ролей без feedback loop → `$qtim-team-lazy`;
- один связный implement → test → fix → review loop → `$qtim-team-up`;
- самостоятельные outcomes, разные contexts/worktrees либо producer → consumer
  → `$qtim-mission`.

Размер и число файлов не выбирают workflow. Глубина локальной команды остаётся
осью [orchestration-patterns.md](orchestration-patterns.md), не этапом фичи.
Recommendation остаётся `RECOMMEND`:
она не запускает реализацию, `spawn_agent` или peer tasks. Явное разрешение
пользователя в том же сообщении с approval достаточно для запуска, дополнительных
стартовых согласований standalone-фаз нет, кроме выбранного phase-by-phase режима
или новой существенной развилки. В feature-sequential действуют ticket acceptance
и отдельное разрешение advance из feature-execution.

Пример готовой команды:

```text
Рекомендация: $qtim-team-up
Почему: один связный outcome с implement/test/fix/review loop.
Топология: WI-01 → WI-02 → verification.
Команда: $qtim-team-up, реализуй Approved spec docs/features/<slug>/spec.md revision <N>.
Альтернатива: direct, если все работы выполняет один исполнитель без fan-out.
```

Для mission команда `запусти` требует уже утверждённого полного graph с
base/integration target, write scopes, budgets и gates. Иначе команда —
`$qtim-mission, preview ...`; пятистрочная recommendation и краткое «запускай
предложенное» не заменяют approval mission preview и не создают peer tasks.
Если пользователь разрешил выполнить показанную preview-команду, подготовь
полный mission preview в режиме `PREVIEW` и дождись его approval.

Проверь dev track marker и нужных writers по затронутым слоям. Наличие PM reviewer
не доказывает готовность dev-команды. При их отсутствии handoff явно включает
`$qtim-setup` для dev track до team execution; planning остаётся завершённым.

После актуального review (либо explicit waiver) и approval main thread сообщает
готовый handoff. Затем **последним файловым изменением** добавляет/обновляет одну
строку на slug, `spec.md` и утверждённую ревизию в `memory/decisions.md`.
Указатель — completion marker handoff, повторная запись идемпотентна.

Resume читает текущую спецификацию, вердикт, ревизии, бюджет и указатель:

- `Draft` (включая workflow `Blocked`) → только открытый вопрос/подтверждённый finding;
- готово к approval → показать эту ревизию владельцу;
- актуально Approved, указателя нет либо он относится к старой ревизии → завершить
  handoff, без нового интервью/review;
- актуальный указатель → planning завершён, ожидать разрешённого исполнения;
- `In Development`/`Done`/`Archived` → существующий execution/lifecycle, без
  перезапуска planning. Существенная дельта обрабатывается правилами ревизий.

В feature-sequential статус spec — производная сводка coordinator по ledger:
при разрешённом старте → `In Development`, только после всех required tickets,
stage gates, финальной интеграционной проверки и приемки владельца → `Done`.
При standalone/legacy исполнении сохраняются прежние AC/gates и их status lifecycle.
`Archived` требует проверенного Done, свидетельства слияния и решения
владельца. Spec и короткий указатель сохраняются; очистка `.work/` — только по
решению владельца. Остановка команды сама по себе не означает Done.
`История изменений` содержит максимум пять коротких существенных записей;
старые закрытые записи сжимаются, без копирования всей процессной истории.

## Legacy adapter

Существующие `intake.md`, `prd.md`, `decomposition.md`, `estimate.md`, `plan.md`
и `feature-brief.md` остаются долговечными источниками прежней фичи. Их чтение
не запускает конвертацию, удаление, повторное согласование или генерацию новой
цепочки документов. Утверждённые `plan.md`/brief продолжают разрешённое исполнение
с прежними AC, gates и указателем; наличие недоступного тогда SPEC_REVIEW не
отменяет исторический approval.

Approved `prd.md` с `Результат: PRD-only` — терминальный результат без команды
реализации. Незавершённое legacy-планирование прочитай как context; прежде чем
перейти на spec, получи отдельное решение владельца о конвертации, сохранив
старые документы и принятые решения. Если одновременно есть spec и legacy,
проверь историю и явный выбор источника; вопрос нужен только при реальном
неразрешённом конфликте. Миграция плагина сама feature-документы не переписывает.

Approved spec-only без tickets также остаётся действующим. На resume предложи
конкретный adapter: сопоставь существующие WI/AC/gates с Stage/Ticket и сохрани
источники, принятые решения и подтверждённо актуальное evidence. Только после
отдельного решения владельца добавь ticket contracts и согласуй affected revisions
по правилам выше; старый approval не принимает новые контракты автоматически.
Новый `plan.md` для адаптации не создаётся. Продолжение прежнего разрешённого
standalone/team/lazy/mission workflow не требует принудительной конвертации.
