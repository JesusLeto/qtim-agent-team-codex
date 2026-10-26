---
name: qtim-feature
description: "Turn a raw feature idea into one revisioned specification through a decision interview, mandatory independent specification review, user approval, and implementation handoff; resume an existing feature without reopening settled decisions."
---

# qtim Feature

Интервью → одна спецификация с независимым ревью → утверждение → handoff.
Этот вызов разрешает bounded read-only consult и обязательный reviewer, но не
production code, SQL, тесты или запуск реализации.

Канон документа, ревизий, принятого scope и legacy adapter —
`../../reference/feature-pipeline.md`; бюджет и независимость review —
`../../reference/independent-review.md`. Main thread — единственный редактор spec.

## Preconditions и resume

1. Прочитай `.codex/team-charter.md` и PM marker `<!-- qtim:track:pm:start -->`.
   Если их нет, предложи `$qtim-setup` до planning.
2. Прочитай feature-pipeline, intake-protocol и model-profiles в `../../reference/`.
   Main lead — `gpt-6-astra` + `ultra`; другой явно показанный профиль не меняй
   скрыто, останови fan-out и попроси новый task на Astra/Ultra.
3. Определи kebab-case slug. Если каталог существует, прочитай действующий источник,
   решения, review budget и указатель. Используй resume/legacy adapter reference;
   отсутствие указателя при актуальном Approved spec означает завершение handoff,
   а не новое интервью. Legacy `feature-brief.md`/`prd.md` не конвертируй автоматически.
4. До записи `docs/features/` или `memory/` прочитай `$qtim-kb-format`.
   Consult/raw review/логи — в `.work/`; контракт — один `spec.md`.

Роли и fallbacks запускай по model-profiles: сохраняй явные пары и пользовательские
overrides, учитывай уже подтверждённую недоступность runtime. Prompts/follow-ups
агентам — English, spec и общение с пользователем — Russian.

## 1. Интервью

Прочитай существующую product memory, если она создана. Отсутствие product onboard
не блокирует planning. Последовательно выясни проблему и пользователя, поведение,
приёмку, ограничения и non-goals. Задавай **один вопрос за раз**, с рекомендуемым
ответом и коротким основанием; следующий вопрос учитывает предыдущий ответ.
Факты из кода, memory, git и доступных документов добывай сам.

Точечный consult нужен лишь для названного неизвестного факта: один вопрос,
граница чтения и ожидаемый evidence. Независимые вопросы должны иметь disjoint
scope; role ownership реализации не требует обязательного planning fan-out.
Product по умолчанию не запускается. Child agents не делегируют дальше.

Сохраняй ответы и `D-*` в Draft `spec.md`. Заверши интервью после разрешения
вопросов, влияющих на scope, поведение, контракты и AC. Не создавай промежуточный
intake approval. Новый противоречащий факт возвращает только затронутое решение.

## 2. Спецификация и независимое ревью

Собери spec по reference: AC, подтверждённые решения, одна WI-таблица с ownership,
файлами, порядком, зависимостями и review boundaries, gates, риски и rollback.
Небольшая фича получает короткий документ, большая — больше проверяемых срезов;
отдельных full/fast процессов и артефактов нет. Оценку добавляй лишь по реальному
запросу/решению, без отдельного checkpoint.

Заранее заполни handoff и Execution Recommendation Gate по topology reference,
включая нужный dev track/writers. Reviewer в PM roster сам по себе не dev-ready.
Если возник настоящий ADR, сохрани обязательный clean-context ADR adversary до
approval; обычная спецификация не создаёт ADR или дополнительный review лишь
из-за размера/ярлыка риска.

Main thread запускает существующего `qtim-reviewer` в `SPEC_REVIEW` по
independent-review: механически read-only, чистый контекст (`fork_turns = "none"`),
минимальный source pack без авторской истории. Передай текущую ревизию, raw
требования/ответы владельца, spec, инварианты и проверяемые источники.
Reviewer возвращает `READY_FOR_APPROVAL` либо `CHANGES_REQUESTED` с evidence и
затронутыми `AC-*`/`D-*`/`WI-*`; build/tests/browser в planning не запускает.

Проверь findings по источникам. Подтверждённые blockers исправь; предпочтения и
неподтверждённые claims отклони с причиной. Сохрани краткий исходный verdict,
dispositions, Reviewed revision и бюджет в spec. Разрешены один полный проход и
максимум один fix/targeted-recheck, с неизменным бюджетом при resume/revision labels.
Непреодолённый blocker либо необходимость нового полного прохода сверх бюджета
→ `Blocked` и конкретное owner decision. Недоступное обязательное review не
подменяй self-review: поддерживаемый независимый fallback или явный recorded
owner waiver по reference. Пропуск не обозначай PASS.

## 3. Утверждение

Покажи спецификацию, результат независимого review и готовую рекомендацию запуска.
Попроси **одно** approval конкретной ревизии, только после закрытия подтверждённых
блокеров. Зафиксируй `Approved revision` и Status по reference.
Существенная правка после review/approval возвращает затронутый контракт в Draft;
новый номер ревизии не даёт новый review budget автоматически.

## 4. Handoff

При актуальном review/approval сообщи сохранённую команду и её границы. Последним
файловым изменением идемпотентно обнови одну строку-указатель в `memory/decisions.md`.
Не перепроектируй spec и не запускай проверки реализации после approval.

Recommendation — только `RECOMMEND`. Явное «утверждаю и запускай показанную команду»
разрешает выбранное исполнение без ещё одного стартового вопроса. Mission требует
своего Approved preview; feature handoff его не заменяет. Проверки исполнения
переиспользуются по orchestration-patterns, сохраняя реальные AC/gates и актуальность.

Planning завершён после актуального указателя; реализация начинается только в
разрешённом execution workflow. Новый неподтверждённый scope, отсутствие reviewer
или чужое мнение не превращай в незаметное расширение утверждённой фичи.
