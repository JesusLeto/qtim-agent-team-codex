---
name: qtim-feature
description: "Use when a PM or analyst wants to turn a raw feature idea into versioned artifacts under docs/features: select a risk-proportional fast-path brief or the full intake-to-PRD-to-plan pipeline, optionally finish at an approved PRD, and recommend an execution route only when an implementation plan exists."
---

# qtim Feature Pipeline

Веди хотелку от идеи до утверждённого handoff. Этот вызов явно разрешает нужный read-only fan-out: `qtim-product`, `qtim-architect`, владельцы затронутых dev-слоёв и built-in `explorer`.

Production code не пиши. Артефакты содержат требования, evidence, контракты, инварианты и gates, а не будущие диффы.

Этот skill владеет **сессионной оркестрацией**: порядком стадий, checkpoints, resume,
выбором трека и selective fan-out. Долговечный канон артефактов, статусов, handoff,
grounded-оценки и vertical slicing живёт в `../../reference/feature-pipeline.md`.
Сгенерированный PM-блок charter — производная self-contained сводка этого reference,
а не третий независимый канон.

## Preconditions

1. Прочитай `.codex/team-charter.md`. Если файла или PM track marker `<!-- qtim:track:pm:start -->` нет, остановись и предложи `$qtim-setup`.
2. Прочитай `../../reference/feature-pipeline.md` и `../../reference/intake-protocol.md`.
3. Прочитай `../../reference/model-profiles.md`. qtim team-lead должен работать на `gpt-6-astra` + `ultra`; не переключай уже открытый task скрыто. Если runtime exposes другой профиль, остановись до fan-out и попроси открыть новый task на Astra/Ultra. `Ultra` не расширяет scope и не отменяет checkpoints.
4. Определи kebab-case slug.
5. Если `docs/features/<slug>/` существует, прочитай статусы и «Историю изменений». `feature-brief.md` означает fast-path, `prd.md`/полный набор — полный трек. `Archived` завершён; `Done` сначала проверь по gates. Approved PRD-only с указателем — завершённое планирование до новой просьбы продолжить. Иначе продолжи с первого незавершённого обязательного артефакта, не начинай заново. У Stage 6 своего артефакта нет: её completion marker — строка-указатель на slug в `memory/decisions.md`. Approved план, brief или PRD-only без указателя -> resume со Stage 6.
6. Перед первой записью в `docs/features/` или `memory/` прочитай `$qtim-kb-format`; передай его правила каждому пишущему агенту. Уже существующие артефакты меняй на месте и сжимай их историю, не дописывай копии.

Если custom agent не стартует именно из-за model pair, не удаляй пару и не заменяй её inheritance молча. Отличающийся override сохрани; продолжи через `worker` с inline role instructions только на явно подтверждённой доступной pair. Built-in `explorer` используй на `gpt-6-luna` + `medium`; не угадывай slug и не считай auth/network ошибку несовместимостью модели.

Все prompts и follow-ups для consult/subagent ролей пиши на English. Артефакты `docs/features/**`, checkpoints и всё, что передаётся пользователю, пиши на Russian по обязательному project language contract.

## Artifacts

Общий файл — `intake.md`. Полный трек добавляет `prd.md`, `decomposition.md`, `plan.md` и условный `estimate.md`; fast-path — один `feature-brief.md` вместо них. PRD-only завершает планирование после утверждённого `prd.md`. Шапка, статусы Draft -> Approved -> In Development -> Done -> Archived и «История изменений» с потолком в пять коротких записей — по feature-pipeline reference. `memory/decisions.md` хранит только указатель на утверждённую фичу.

## Stage 1: Intake And Track

Сначала прочитай продуктовую память, если создана: `memory/product-map.md`, `product-actors.md`, `product-glossary.md`, `product-metrics.md`. Если её нет в существующей кодовой базе, предложи `$qtim-product-onboard`, но не блокируй работу.

Проведи итеративное интервью порциями по 1-3 решения. Факты из кода, `memory/`, git и документации добывай сам. Сначала выясни проблему, пользователя и желаемый результат; затем критерии успеха, ограничения, совместимость и non-goals. Остановись, когда ответы перестали менять понимание.

Запиши `intake.md`. На checkpoint покажи:

- сводку понимания;
- предварительный размер и число фаз с evidence;
- результат Fork Test из intake protocol;
- рекомендуемый трек.

Предлагай **fast-path** только для S/M, одной фазы и без Fork Test triggers. Иначе — полный трек. Пользователь подтверждает понимание и может переопределить трек; зафиксируй выбор и переведи intake в Approved.

## Fast-path: Feature Brief

Собери `feature-brief.md` сам. Обязательного веера ролей нет: evidence найди чтением и точечным `explorer`; уже активную профильную роль используй только по реально затронутому слою. DRI и contributing роли/слои здесь задают ownership реализации, а не обязательный planning fan-out. Единый размер S/M обоснуй кодовым evidence; если уже консультировал профильную роль, учти её оценку как signal. Не можешь обосновать contributing layer или видишь правдоподобный L/XL — переходи на полный трек.

Brief включает:

- проблему, желаемый результат, сценарии с acceptance criteria и non-goals;
- work items с DRI, contributing ролями/слоями и привязкой к файлам;
- размер S/M с evidence-обоснованием;
- одну проверяемую фазу: gates, rollback/обратимость, Done;
- `## Handoff` для `$qtim-team-lazy`.

**Единственный checkpoint вместо стадий 2-5:** пользователь утверждает brief целиком; Status -> Approved.

Если при сборке возникла развилка, L/XL или больше одной фазы, разверни полный трек: сохрани intake, переименуй незавершённый brief в `prd.md`, перестрой его как Draft PRD, запиши причину перехода в историю и продолжи со стадии PRD. Не поддерживай одновременно два конкурирующих плановых документа.

После approval переходи к Handoff.

## Full Track Stage 2: PRD

Spawn `qtim-product` (fallback: `worker` с PM-инструкциями из charter) с read-first на charter PM track и `intake.md`.

`prd.md` содержит цели, non-goals, сценарии и acceptance criteria, UX-заметки, метрики, риски, open questions. Метрики связывай с реальными событиями из `memory/product-metrics.md`; отсутствующее событие — задача на tracking, не факт. **Checkpoint:** пользователь утверждает PRD и выбирает «продолжить к плану» либо «завершить на PRD». Если выбрано второе, добавь `## Handoff` с `Результат: PRD-only` и открытыми решениями, Status -> Approved, затем выполни только PRD-only ветку Stage 6. Возобновляй стадии 3-5 лишь по новой просьбе пользователя.

## Full Track Stage 3: Grounded Decomposition

Состав consult пропорционален задетым слоям:

1. Spawn read-only `qtim-architect` для слоёв/data flow/инвариантов и только нужные `qtim-database`, `qtim-frontend`, `qtim-testing`; узкая фича обычно требует architect + одного владельца слоя. `explorer` — broad search. Уважай runtime cap и запускай batches; child agents не делегируют дальше.
2. `qtim-product` агрегирует `decomposition.md`: `id | вертикальный work item | DRI | contributing роли/слои | зависимости | grounding (файлы)`. DRI владеет главной acceptance boundary; неоднозначный ownership разрешает architect.

Каждый work item — проверяемый вертикальный срез через затронутые слои. Очевидный XL item разрежь даже при пропуске оценки. Для широкого механического rename/retype используй expand-contract. Checkpoint для decomposition общий со Stage 4, если оценка нужна; иначе пользователь утверждает work items без отдельного раунда оценки.

## Full Track Stage 4: Grounded Estimation, When Needed

По умолчанию пропусти Stage 4 и `estimate.md`. Выполни её, если оценка нужна
для выбора исполнителя, срока/бюджета или явно запрошена. Передача тому же
владельцу в новую задачу Codex сама по себе не требует оценки. Decomposition
и разрезание XL остаются обязательными в обоих случаях.

Каждая contributing роль даёт S/M/L/XL + confidence + риски для своего layer slice с evidence (файлы, покрытие, интеграционные точки, reference class из git или `memory/decisions.md`). DRI возвращает один итоговый размер vertical item с явным синтезом integration/coordination risk; не складывай размеры механически. Без evidence оценка не принимается; XL любого slice или item означает вернуться к decomposition и разрезать item.

Если Stage 4 нужен, `qtim-product` сводит `estimate.md`. **Checkpoint:**
пользователь утверждает work items; при выполненной оценке одним решением
утверждает и её, оба созданных артефакта -> Approved. Если Stage 4 пропущен,
Approved получает только `decomposition.md`. При изменении состава пересчитай
оценки затронутых items, только если `estimate.md` существует.

## Full Track Stage 5: Plan

`qtim-product` + `qtim-architect` собирают `plan.md`:

- проверяемые вертикальные фазы с work items;
- disjoint write scopes, которые можно параллелить;
- typecheck/build/tests/browser gates;
- rollout, rollback и обратимость;
- критерий Done.

Сначала ставь решения с высокой неопределённостью (данные, API-контракты, UX-развилки), механическую доводку — позже. Широкий рефактор планируй expand-contract.

Если architect создал ADR, **до** финального checkpoint main thread запускает новый read-only thread без истории на `gpt-6-astra` + `xhigh`; при сочетании «необратимо + затронут документированный инвариант» — `max`. Findings возвращаются architect для проверки, а ADR получает строку `adr-stress-test:`. Исправления и повторные проходы ограничены `../../reference/independent-review.md`; optional code-review gate этот шаг не отключает.

**Checkpoint:** финальное approval; Status -> Approved.

## Stage 6: Handoff

Для `PRD-only` сохрани `## Handoff` и сообщи пользователю, что продуктовый
контракт готов. Затем последним файловым изменением добавь или обнови одну
строку-указатель на `prd.md` в `memory/decisions.md`. Команду реализации и блок
`Что запускать дальше` пока не создавай: сначала нужна новая просьба
продолжить планирование.

Для утверждённого плана или brief выполни шаги ниже:
Его approval закрывает design gate для реализации и всех предусмотренных фаз.
После отдельного разрешения запуска исполнение не требует вопроса перед каждой
фазой, кроме новой существенной развилки или выбранного phase-by-phase режима.

1. Для полного трека сначала заверши `plan.md` базовым implementation contract:

```text
PRD и acceptance criteria: docs/features/<slug>/prd.md.
Обнови Status артефактов: In Development при старте, Done после gates.
После проверки Done и свидетельства слияния предложи архивацию владельцу по feature-pipeline reference.
Отклонения и новые edge cases фиксируй в «Истории изменений» plan.md.
```

2. Для fast-path заверши brief:

```text
Scope, acceptance criteria и gates находятся в этом документе.
При старте переведи Status в In Development, после всех gates — в Done.
После проверки Done и свидетельства слияния предложи архивацию владельцу по feature-pipeline reference.
Отклонения и новые edge cases фиксируй там же.
```

3. Проведи обязательный **Execution Recommendation Gate**. Выбирай форму по
   topology, а не по размеру:
   - один bounded outcome без fan-out -> direct;
   - один outcome, нужны несколько точечных ролей, feedback loop не ожидается ->
     `$qtim-team-lazy`;
   - один связный outcome и implement -> test -> fix -> review loop ->
     `$qtim-team-up`;
   - два и более самостоятельных outcomes, разные контексты/worktrees или
     dependency producer -> consumer -> `$qtim-mission`.
   Размер `S/M/L/XL` влияет на декомпозицию и стоимость, но не переопределяет
   topology. XL с одним feedback loop остаётся team-up; M producer -> consumer
   может требовать mission.
4. Добавь в плановый документ блок `## Что запускать дальше`:

```text
Рекомендация: $qtim-mission
Почему: <самостоятельные outcomes / dependency / context isolation / feedback loop>
Топология: <A -> B -> verification или один связный loop>
Команда: $qtim-mission, <запусти|preview> Approved feature docs/features/<slug>/.
Альтернатива: $qtim-team-up для одного связного outcome с feedback loop.
```

   Для direct, team-lazy и team-up сохрани те же пять полей; команда должна быть
   готова к копированию. Recommendation — режим `RECOMMEND`: он не разрешает
   `spawn_agent`, `create_thread` или реализацию. Для Approved graph с готовыми
   base/integration target, write scopes, budgets и gates допустима команда
   `запусти`; unresolved writer/lazy/runtime choice получает `preview`.
5. Если charter содержит только PM track и нет `qtim-reviewer`, предупреди: перед
   реализацией нужно повторно вызвать `$qtim-setup` и добавить dev track, иначе
   team-up/mission останутся без обязательного verification gate.
6. Если реализацию запускает другой человек, попроси его использовать готовую
   команду в новой задаче Codex. Выполнение displayed команды — явный вызов
   выбранного workflow. Короткое «Запускай предложенное» после feature
   recommendation выбирает workflow, но для `$qtim-mission` сначала открывает
   `PREVIEW`: этот пятистрочный handoff не является полным Approved mission
   preview. Peer tasks появляются только после explicit mission-команды либо
   approval на непосредственно предшествующий полный preview; завершение feature
   само ничего не запускает.
7. **Последним шагом** добавь одну строку-указатель в `memory/decisions.md`. Это
   atomic completion marker Stage 6: записывай его только после того, как handoff
   и блок «Что запускать дальше» сохранены и сообщены пользователю.

## Anti-Patterns

- Full track на простой S/M-хотелке без развилок или fast-path при Fork Test trigger.
- Отдельные approvals decomposition и estimate.
- Fan-out всех ролей независимо от затронутых слоёв.
- Горизонтальные work items «вся БД / весь UI» вместо вертикальных срезов.
- Production code, SQL, тесты или будущие диффы в артефактах.
- Перезапуск существующего slug с нуля.
- Плановый документ `Approved`, но указателя в `memory/decisions.md` нет: Stage 6 оборвана и должна быть продолжена.
- Указатель записан до готового handoff: ложный completion marker ломает resume.
- Выбор workflow только по S/M/L/XL или числу файлов вместо outcomes, dependencies,
  context/worktree isolation и feedback loops.
- Автоматический запуск рекомендованного `$qtim-team-up`/`$qtim-mission` без нового
  явного разрешения пользователя.
- Выдуманные часы вместо относительной оценки с evidence.
- Обязательная стадия estimate без решения, которому нужна оценка.
- Продолжение к плану после выбранного результата `PRD-only` без новой просьбы.
- Пропуск checkpoint «потому что очевидно».
