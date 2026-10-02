# Feature-pipeline qtim для Codex: долговечные контракты

> Generic reference qtim. Проектные инварианты и роли живут в `.codex/team-charter.md`;
> здесь — контракты, переживающие сессию: схемы артефактов, статусы, handoff,
> grounded-оценка и vertical slicing. Порядок стадий, checkpoints, resume и fan-out
> принадлежат `$qtim-feature`. Setup переносит производную self-contained сводку этого
> reference в PM track charter; сводка не становится независимым каноном.

## Принцип

PM-трек документирует, dev-трек реализует. Церемония пропорциональна риску, а не самому ярлыку «фича»:

- **Полный трек** — многофазная фича, размер L/XL или сработало хотя бы одно условие Fork Test из [intake-protocol.md](intake-protocol.md). При планировании реализации выход — четыре обязательных артефакта (`intake`, `prd`, `decomposition`, `plan`) и условный `estimate.md`; после approval PRD возможен ранний выход.
- **Fast-path** — S/M-хотелка в одну фазу без развилок. Стадии PRD/decomposition/estimate/plan заменяет один `feature-brief.md` с единственным checkpoint после Intake.

Трек предлагает main thread после Intake; пользователь подтверждает или переопределяет его на checkpoint. Если внутри fast-path обнаружилась развилка или многофазность, сохрани `intake.md`, переименуй незавершённый `feature-brief.md` в `prd.md`, приведи его к PRD-формату и продолжи полным треком. Зафиксируй переход в «Истории изменений».

Артефакты версионируются в `docs/features/<slug>/`. `memory/` хранит только решения и указатели, не содержимое документов.

## Артефакты и статусы

| Файл | Содержимое |
|---|---|
| `intake.md` | исходная хотелка, уточнения, подтверждённый трек |
| `prd.md` | полный трек: цели, сценарии, acceptance criteria |
| `decomposition.md` | полный трек: work items с привязкой к слоям и файлам |
| `estimate.md` | полный трек, когда оценка нужна для выбора исполнителя, срока/бюджета или прямо запрошена: grounded S/M/L/XL |
| `plan.md` | полный трек: фазы, gates, handoff |
| `feature-brief.md` | fast-path: PRD-lite, grounded work items, план одной фазы, gates и handoff |

Каждый файл начинается с шапки:

```text
Feature: <название>
Slug: <slug>
Status: Draft | Approved | In Development | Done | Archived
Дата: YYYY-MM-DD
```

и заканчивается секцией `## История изменений`: максимум 5 коротких записей о
ревизии, смене трека или существенном отклонении от плана. При превышении лимита
сожми старые записи в одну строку с итогом; долговечное решение оставь в
основном артефакте или ADR, процессную историю вынеси в `.work/` только пока
фича активна. Не превращай этот раздел в журнал каждого шага.

`Done` означает, что acceptance и обязательные gates реально пройдены.
`Archived` ставится только после проверки `Done` и свидетельства слияния
результата, с решением владельца об архивации. Сохрани `prd.md`/`plan.md` или
`feature-brief.md` и durable evidence, обнови существующий указатель в
`memory/decisions.md` одной короткой строкой с итогом. Удалять можно только
одноразовые материалы `docs/features/<slug>/.work/`, также по решению владельца;
архивацию и очистку предложи одним пакетом. Явная просьба пользователя в
текущей задаче считается решением. Остановка команды сама по себе не доказывает
`Done`; существующие `Done` остаются валидными без архивации.

Resume-правило: если каталог уже существует, не начинай заново. `feature-brief.md` означает fast-path; `prd.md`/полный набор — полный трек. `Archived` означает завершённый результат; `Done` не требует автоматической архивации. Иначе продолжай с первого обязательного артефакта, который не достиг `Approved`; отсутствующий условный `estimate.md` не блокирует resume. Если `prd.md` утверждён с `Результат: PRD-only` в `## Handoff`, это терминальный результат планирования: продолжай к decomposition только по новой просьбе пользователя. Если Approved `plan.md`, `feature-brief.md` или PRD-only `prd.md` не имеет указателя на slug в `memory/decisions.md`, Stage 6 оборвана: продолжай Handoff. Если набор неоднозначен, прочитай историю `intake.md` и попроси решение только если она не разрешает конфликт.

## Стадии и checkpoints

| Стадия | Кто работает | Выход | Checkpoint |
|---|---|---|---|
| 1 Intake | main thread / product | `intake.md` | пользователь подтверждает понимание и трек |
| 2 PRD | product | `prd.md` | пользователь утверждает PRD и выбирает продолжение к плану или завершение на PRD |
| 3 Decomposition | product + dev-consult | `decomposition.md` | общий со стадией 4, если оценка нужна; иначе утверждение work items |
| 4 Estimation | владельцы слоёв + product, если нужна оценка | условный `estimate.md` | пользователь одним решением утверждает work items и оценки, если они есть |
| 5 Plan | product + architect | `plan.md` | финальное approval |
| 6 Handoff | main thread | указатель в `memory/decisions.md` на Approved план/brief либо PRD-only | — |

Fast-path заменяет стадии 2-5 одним `feature-brief.md`; стадии 1 и 6 общие.
Выбор `PRD-only` после Stage 2 завершает полный трек без стадий 3-5: `prd.md`
содержит `## Handoff` с `Результат: PRD-only` и открытыми решениями, но без
команды реализации. Для возобновления планирования нужна новая просьба.

## Fast-path brief

Main thread собирает brief сам. Обязательного fan-out ролей нет, но evidence остаётся обязательным: читай ключевые файлы, используй built-in `explorer` для широкого поиска или уже активную профильную роль для точечного consult.

DRI и contributing роли/слои в brief задают ownership реализации, а не обязательный planning fan-out. Main thread обосновывает единый размер S/M кодовым evidence; оценку уже привлечённой профильной роли учитывает как дополнительный signal. Если evidence не позволяет обосновать хотя бы один contributing layer или появляется правдоподобный L/XL, переключайся на полный трек с layer estimates.

`feature-brief.md` содержит:

- проблему, желаемый результат, сценарии с acceptance criteria и не-цели;
- work items с DRI, contributing ролями/слоями и привязкой к конкретным файлам;
- размер S/M и одну строку evidence-обоснования;
- одну фазу с verification gates (typecheck/build/tests, browser evidence для UI), rollback/обратимостью и критерием Done;
- секцию `## Handoff`.

Пользователь утверждает brief целиком; после approval переходи к handoff и выбирай
следующий workflow по execution topology. Размер S/M не исключает `$qtim-mission`,
если brief действительно содержит самостоятельные producer/consumer outcomes.

## Dev-consult полного трека

На стадиях 3-4 architect проверяет слои, data flow и инварианты; database/frontend/testing — только реально затронутые слои, каждый возвращает затронутые файлы, интеграционные точки, похожие фичи и риски. Узкая фича обычно требует `qtim-architect` и владельца одного слоя, а не веер всей команды. Consult read-only; вывод ролей — evidence для product. `explorer` используй для broad read-heavy поиска.

Состав work items и существующие оценки утверждаются вместе. Если оценки
пропущены, checkpoint утверждает decomposition; повторный consult не нужен
только ради заполнения `estimate.md`. Если пользователь меняет decomposition,
пересчитай оценки затронутых items, когда они есть.

## Правило нарезки

Work item и фаза плана — вертикальный срез: узкий, но полный путь через затронутые слои (например, схема -> API -> UI -> тесты), который можно продемонстрировать или проверить сам по себе. У каждого item один **DRI** по главной acceptance boundary и список contributing ролей/слоёв; неоднозначного DRI выбирает architect. Горизонтальный план «сначала вся БД, потом весь UI» не подходит.

Исключение — широкий механический rename/retype с blast radius по всей базе. Планируй его через **expand-contract**:

1. добавить новую форму рядом со старой, ничего не ломая;
2. мигрировать call sites небольшими пачками с зелёными gates после каждой;
3. удалить старую форму последним item, когда ссылок не осталось.

## Условная grounded-оценка полного трека

По умолчанию пропусти Stage 4 и `estimate.md`. Выполни её, если оценка нужна
для выбора исполнителя, планирования срока/бюджета или явно запрошена.
Передача тому же владельцу в новую задачу Codex сама по себе не требует
оценки. В обоих случаях разрежь очевидный XL work item на проверяемые срезы
в decomposition.

- Только S/M/L/XL + confidence + риск-факторы; часы и дни не выдумывать.
- Каждая contributing роль даёт оценку своего layer slice с evidence. DRI возвращает один итоговый S/M/L/XL для всего vertical item и коротко объясняет синтез, включая integration/coordination risk; размеры не складываются механически.
- XL любого layer slice или итогового item означает «разрезать work item» и вернуться к decomposition.
- Product сводит layer estimates и DRI synthesis, но не переоценивает техническую работу сам.
- Каждая оценка ссылается на evidence: файлы, тестовое покрытие, интеграционные точки, reference class из git или `memory/decisions.md`.
- Оценка без evidence не принимается.

## Handoff contract

- Полный трек: `plan.md` ссылается на `prd.md` и заканчивается готовой командой
  для direct, `$qtim-team-lazy`, `$qtim-team-up` или `$qtim-mission`.
- Fast-path: `feature-brief.md` — единый источник scope, acceptance criteria,
  gates и готовой команды выбранного workflow.
- PRD-only: `prd.md` — законченный продуктовый контракт с `## Handoff` и
  `Результат: PRD-only`; он не разрешает запуск implementation workflow.
- Каждый Approved плановый документ содержит `## Что запускать дальше` с полями:
  `Рекомендация`, `Почему`, `Топология`, `Команда`, `Альтернатива`.
- Routing определяется формой исполнения:
  - один bounded outcome -> direct;
  - один outcome и несколько точечных ролей без feedback loop ->
    `$qtim-team-lazy`;
  - один связный implement -> test -> fix -> review loop -> `$qtim-team-up`;
  - два и более самостоятельных outcomes, разные contexts/worktrees или
    producer -> consumer -> `$qtim-mission`.
- Размер `S/M/L/XL` влияет на декомпозицию и coordination cost, но не выбирает
  workflow сам. Одинаковая execution topology получает одинаковую рекомендацию.
- Recommendation работает только в режиме `RECOMMEND`: завершение feature не
  запускает subagents или peer-задачи. Нужна новая явная команда пользователя.
- Approved mission graph с готовыми base/integration target, write scopes,
  budgets и gates получает команду `$qtim-mission, запусти ...`. Если writer
  preflight, lazy profile или integration target ещё требуют выбора, команда
  использует `$qtim-mission, preview ...`; `$qtim-team-up` остаётся альтернативой
  для одного связного outcome с feedback loop.
- Короткое «Запускай предложенное» после пятистрочной feature recommendation
  выбирает `$qtim-mission`, но открывает `PREVIEW`, а не создаёт peer tasks:
  recommendation не является полным Approved mission preview. `AUTO-START`
  возможен по displayed explicit mission-команде либо после approval полного
  preview с base/targets/scopes/budgets/gates.
- Реализующая команда переводит плановый документ и связанные артефакты в `In Development`, затем `Done` после gates.
- Отклонения от плана с обоснованием и новые edge cases пишутся в «Историю изменений» планового документа (`plan.md` или `feature-brief.md`).
- В `memory/decisions.md` добавляется одна строка-указатель на утверждённую фичу
  (для PRD-only — на её `prd.md`).
  Это completion marker Stage 6: main thread пишет её **последней**, когда handoff уже
  сохранён и сообщён. Approved план, brief или PRD-only без указателя означает
  оборванный Handoff и требует resume со Stage 6.

## Anti-Patterns

- Полный трек для S/M-хотелки без развилок или fast-path при сработавшем Fork Test.
- Decomposition/estimate без обследования кода нужными владельцами слоёв.
- Product или PM-конвейер пишет production code, SQL или тесты.
- Куски кода/SQL внутри артефактов: документы хранят контракты, инварианты и acceptance criteria, не будущий diff.
- Отдельные checkpoints для decomposition и estimate вместо одного решения.
- Создание `estimate.md` без решения по исполнителю, сроку или бюджету,
  которому нужна оценка, и без явного запроса пользователя.
- Продолжение к плану или реализации после выбранного результата `PRD-only`
  без новой просьбы пользователя.
- Спавн всех consult-ролей по привычке, даже когда их слои не затронуты.
- Горизонтальная нарезка по слоям вместо проверяемых вертикальных срезов.
- Пропуск checkpoint «потому что очевидно».
- Перезапуск существующего slug с нуля.
- Запись указателя в `memory/decisions.md` до готового handoff.
- Выбор workflow только по размеру или числу файлов вместо topology outcomes,
  dependencies, context isolation и feedback loops.
- Автоматический запуск рекомендации без отдельного явного разрешения.
- Молчаливое отклонение от планового документа без строки в истории.
