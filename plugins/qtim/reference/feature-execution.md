# Последовательное исполнение feature tickets

> Контракт для исходного feature coordinator. Worker получает bounded context
> текущего тикета. Формат требований, tickets, ревизии и перенос обязательств —
> [feature-pipeline.md](feature-pipeline.md); бюджет review —
> [independent-review.md](independent-review.md).

Этот reference связывает coordinator prompt с локальным state guard, без нового
production App dispatcher. Перед исполнением нужна проверенная поддержка этих
capabilities; отсутствие безопасного state ownership или отдельных App chats —
Blocked/Unavailable. Subagent и продолжение одного чата не заменяют отдельный
ticket chat. Выбор другого workflow требует решения владельца.

## Артефакты и единственный writer

В `docs/features/<slug>/`:

| Артефакт | Назначение / writer |
|---|---|
| `spec.md`, `adr.md`, `tickets/Txx-<slug>.md` | Продуктовый контракт / coordinator; worker предлагает дельту и останавливается |
| `execution.json` | Единственный live ledger исполнения / coordinator через guard, только после разрешённого start |
| `execution.lock` | Exclusive lock рядом с authoritative ledger / guard; чужой или stale lock не удаляется автоматически |
| `receipts/Txx-aN.md` | Durable проверенная сводка результата и решения владельца / coordinator |
| `.work/Txx/` | Предложение receipt worker, raw logs/patches/review output; только разрешённые writer/scope |

Coordinator не пишет implementation source параллельно worker. Worker не меняет
shared contracts, очередь, ledger или accepted receipts и не создаёт следующего
peer. Локальные роли допустимы только в его bounded scope по правилам проекта;
fan-out не меняет единственного владельца feature. Human status — проекция ledger,
а не независимые live-поля в таблице требований или tickets.

До первого init разрешение исполнения связывает один canonical execution root:
absolute realpath, repository identity, feature ID, exact ledger/lock paths и
coordinator thread/host. Он может отличаться от implementation worktree. Все
state/dispatch операции используют этот root, независимо от cwd; копия ledger
не становится authority. Нет автопоиска по cwd, второго init или восстановления
authority из worker output. Недоступность root/перенос — Blocked до отдельного
решения владельца.

## Ledger: обязательный формат

Сериализуемый ledger содержит следующие связанные данные; неизвестная schema
version или неполный/нечитаемый документ блокирует resume, а не означает empty state.

| Группа | Обязательные данные |
|---|---|
| Identity | Schema version; feature ID; repository и canonical root/ledger/lock identities; coordinator thread/host |
| Revisions | Spec/ADR revisions (`none` без ADR), ticket revisions, execution sequence/revision |
| Plan | Упорядоченная очередь стабильных ticket IDs; current ticket либо none; stage/required membership и ссылки на prerequisites/AC из контрактов |
| Attempts | Ticket/attempt ID, состояние, launch marker/intent, source context, pending handle отдельно от bound peer thread/host |
| Workspace | Для каждого repo: worktree, base SHA, dirty/input fingerprint, разрешённые write paths и git actions |
| Result | Receipt identity/revision/hash, source result identity, AC/gates, review verdict/findings/dispositions, сохранённый review budget |
| Decisions | Точное owner decision: scope/revisions/receipt, acceptance, advance, defer/transfer или stop |
| History | Append-only transitions с sequence, ticket/attempt, прежним/новым состоянием и основанием |

Ledger не содержит секретов, полных transcripts или raw logs. Requirements и
prerequisites остаются в контрактах, ledger связывает их актуальные revisions.
Guard обязан проверять типы/версии, root/owner, expected sequence, уникальность
IDs, существование dependencies, отсутствие циклов, AC coverage и допустимость
перехода. Безопасные feature-local paths не проходят через symlinks и не выходят
за root. Запись: exclusive lock → reread/check → temp на том же filesystem → file
fsync → atomic replace → directory fsync. Только durable checkpoint разрешает
внешний side effect; ошибка durability даёт Unavailable без launch. Это контракт
guard, не обещание механического fencing для произвольного tool call другого чата.

## Переходы и решения

| Событие | Условие и результат |
|---|---|
| Spec approval | Владелец утверждает показанную актуальную ревизию после её review. Само по себе не создаёт ledger/peer и не принимает реализацию |
| Execution start | Явное намерение исполнения, актуальные approvals, root/permissions/capabilities; coordinator фиксирует очередь и текущий Planned ticket |
| Planned → Launching | Принятый predecessor очереди (либо первый ticket), выполненные технические inputs и gate предыдущей стадии; durable launch intent с уникальным ticket/attempt marker до create |
| Launching → Running | Ровно один peer связан с attempt; его read-only preflight подтвердил scope/base/dirty/inputs, coordinator сверил и дал bounded write-go в том же чате |
| Worker completion | Только предложение результата: проверяемый receipt и writer-release; self-report, reviewer или CI отдельно не означают приемку |
| Running → Awaiting acceptance | Coordinator сверил exact ticket/attempt/revisions/result fingerprint, actual diff, AC/checks/review/evidence и освобождение writers; обязательные AC текущего scope доказаны |
| Awaiting acceptance → Accepted | Владелец явно принял точный scope/revision/receipt. Независимое review и окончание worker turn не заменяют это решение |
| Advance | Только coordinator, после Accepted и выполненных prerequisites/stage gates, по явной команде либо заранее утверждённому правилу «после моей приемки переходи» |
| Stage Accepted / Feature Done | Все required ticket acceptances + stage gates / все обязательства + финальная интеграционная проверка + приемка владельца |
| Release | Commit/push/integration/merge/release/deploy требуют соответствующего отдельного разрешения; приемка тикета или Done его не добавляет |

`Blocked` возможен из любого незавершённого состояния: открытый AC, stale result,
неизвестный writer, несогласованный контракт или недоступный обязательный стенд.
`Deferred` — только owner decision с переносом по feature-pipeline; не Accepted
и не закрытый final gate. `Stopped` прекращает продвижение, но не доказывает
остановку процесса. Coordinator использует доступный stop control и проверяет
фактическое завершение; новый writer запрещён до подтверждённого release.

Отклонённая приемка/подтверждённый дефект возвращает текущий ticket в Blocked для
bounded fix, не запускает соседа. После разрешения причины coordinator возобновляет
тот же связанный attempt с новым write-go, если inputs/revisions сверены. Потеря
peer требует нового attempt **того же ticket**, нового preflight/launch и сохранения
review budget/history. Из Awaiting acceptance исправление также требует нового
write-go, повторной проверки результата и release; прежнее разрешение записи погашено.

## Receipt и передача worktree

Worker предлагает receipt в `.work/Txx/`:

- ticket/attempt и точные ticket/spec/ADR revisions;
- repo/worktree/base, полный changed paths list и result identity: commit SHA либо
  hash tracked patch + hashes untracked файлов; один HEAD не покрывает dirty code;
- каждый AC: expected → actual/evidence → PASS/FAIL/BLOCKED, команды/exit codes,
  окружение, review verdict/dispositions, CI если применим, limitations/open gates;
- process/subagent runtime handles либо none, их завершение и writer-release.

Coordinator проверяет фактический diff и result fingerprint, не только сообщение.
Перед Awaiting acceptance он сверяет окончание worker turn и связанных writers
по доступным runtime/process evidence, затем повторно fingerprint результата.
Неизвестный процесс или меняющийся результат — Blocked. После release write-go
погашен; следующее исправление получает новое bounded разрешение тому же attempt.
Новый чат не требует нового worktree: последовательный exclusive handoff допустим.
Чужие staged/untracked edits сохраняются; local env/seeds/proxy не входят в поставку.

Проверенный coordinator receipt сохраняет AC/evidence/result/review/открытые gates
и точное owner decision, когда оно получено. Существенное evidence сохраняют в
разрешённом durable месте до очистки raw `.work/`. Accepted receipts не удаляются
вместе с raw logs. Повторное использование evidence — по
[orchestration-patterns.md](orchestration-patterns.md); schema receipt сама не
превращает harness/static/CI evidence в live integration/native/E2E PASS.

## Recovery boundary

`status` только читает. `resume` в исходном coordinator chat сверяет ledger,
root/owner/sequence, revisions, peer и workspace/result. Автоматического takeover
или lease нет; потеря coordinator — Blocked до отдельного owner-approved решения.

Неопределённый исход create требует reconciliation по exact marker, project,
source context и attempt: один найденный peer можно bind, ноль при неизвестном
исходе или несколько — Blocked без слепого повторного create. Pending handle не
является threadId. На restart/stop также обязателен writer-release прежнего writer.
Наблюдаемое создание peer worker-ом — нарушение authority, а не разрешённый
handoff: coordinator блокирует продвижение и выясняет scope/ownership.

Формат документов не подтверждает live recovery, App dispatch или работу guard.
Нельзя обещать фоновое наблюдение без доступного runtime; окончание coordinator
turn само по себе не запускает следующий ticket.

## Guard CLI и совместимость

Helper — `../skills/qtim-feature/scripts/feature_state.py`, stdlib Python.
Команды `status`, `resume`, `init`, `transition` всегда получают explicit `--root`,
`--feature`, `--repository`. `init`/`transition` дополнительно требуют
`--owner-thread`/`--owner-host`, transition — `--expected-sequence` из последнего
проверенного checkpoint. `resume` также сверяет owner; `status` только читает.
JSON payload идет в stdin; exit codes: 0 success, 2 invalid, 3 conflict,
4 blocked, 5 unavailable. Ошибка не дает разрешения внешнего side effect.

Schema `qtim-feature-state/2` проверяется строго. Unknown schema, `/1` и ручной
ledger не конвертируются; init поверх existing ledger запрещен. Новый helper не
является разрешением мигрировать уже идущий процесс или копировать его root.
POSIX descriptor-relative no-follow и directory fsync обязательны; unsupported
runtime, включая Windows без этих primitives, — Unavailable. JSON/artifact reads
и точные serialized ledger bytes ограничены 4 MiB; oversized output отказывает
до temp/replace. Поддерживаемый Python minimum этим контрактом не объявляется.

`init` принимает `{plan, decision}`. PLAN содержит spec/ADR SOURCE refs, ticket
contracts/AC/dependencies, queue/stages/final gates, workspaces/input snapshot.
TASK.scope содержит ordered nonempty spec byte spans `{start,end}` и ADR spans
(пустой список при отсутствии ADR); их полноту coordinator проверяет до approval.
Snapshot — patch REF + file/untracked hashes и identity, учитывающая workspaces.
Guard проверяет перечисленные bytes/scope; полнота Git inventory/diff и semantic
context остаются независимой проверкой coordinator. Один HEAD этого не заменяет.

Именованные transitions и exact JSON examples исполняются existing repo runner
`.github/scripts/check_feature_state.py`: launch/pending/reconcile/write-go,
result/writer-release/await/accept/advance, block/stop, review-reserve/complete,
gate/done, revise/transfer. Это source-fixture reference; target project не обязан
копировать validator. Произвольного JSON patch события нет.

## App dispatch и bounded context

Перед writer start через tool discovery проверь callable schemas create/list/read/
wait/follow-up и их permissions. Отсутствие обязательной capability — Unavailable,
без подмены App peer subagent-ом. Planning не создает implementation ledger/peer;
status не init/reconcile/write-go и не исправляет даже stale state.

Текущая App surface требует прямую human authorization для создания отдельного
чата и follow-up. Сохрани точное исходное поручение и разрешенный scope; пересылка
worker/coordinator сама этих прав не добавляет. Не создавай повторный approval
checkpoint, когда соответствующее поручение владельца уже есть.

1. `list_projects` дает opaque projectId/path/host и isGitRepository. Используй
   соответствующий local project. `create_thread` получает target
   `{type:"project",projectId,environment:{type:"local"}}`, prompt и title.
   Schema не выбирает произвольный existing worktree/cwd: передай physical source
   path и exact fingerprint в prompt, worker проверяет его до любых edits.
   Новый App worktree используй лишь при явном разрешении и согласно текущей
   schema; dirty baseline не обещай автоматически скопированным.
2. Context pack: coordinator/root/ledger/lock identity; ticket/attempt/marker;
   exact current ticket и нужные spec/ADR sections/revisions/hashes; applicable
   AGENTS/charter и профильная memory; узкие Accepted dependency receipts; physical
   repo/worktree/base/index/staged/dirty inventory; write scope/git permissions;
   gates/budget и stop conditions. Не передавай все tickets/transcripts/raw logs.
   Worker может читать необходимый код; shared contracts/ledger/queue пишет только
   coordinator, worker proposal/raw evidence — только разрешенный `.work/Txx/`.
3. Guard `launch` сохраняет intent `{marker,project,context_sha256,decision}` и
   проверенный input. Только новый successful durable response с `dispatch`
   разрешает один `create_thread`. model/thinking опускай для configured default
   peers, пока пользователь прямо не запросил override; local role canon остается
   в model-profiles, не наследуется автоматически от coordinator.
4. Ready response содержит threadId/hostId; pending — clientThreadId. Сохрани
   pending событием `pending {handle}`. Pending handle не передается в APIs,
   требующие threadId. Для ready и recovery используется `reconcile`, не выдуманный
   bind API: candidates содержат exact marker/project/context_sha256 и peer.
5. Ошибка create/потерянный response — unknown outcome. `list_threads` с нужным
   host и pagination, затем bounded `read_thread` проверяют исходный prompt,
   marker, ticket/attempt/source, project и peer identity. Summary/title — hints,
   не proof; title может быть нормализован. Неполная выборка/недоступные данные
   остаются unknown. Ноль при unknown или несколько кандидатов → Blocked; ровно
   один проверенный candidate → reconcile. Blind retry create запрещен.
6. Read-only preflight worker сверяется с actual files независимо от его PASS.
   Guard `write-go {id,preflight,observed}` связывает актуальный input/result;
   только затем authorized follow-up в тот же bound chat разрешает edits.
   Потеря чата требует release и новый attempt того же ticket; budget сохраняется.
7. `wait_threads` принимает максимум восемь targets; для текущего peer используй
   один `{threadId,hostId,afterCursor}`. Read thread нужен для конкретного
   preflight/result/review decision, а не для повторного полного transcript.
   Worker completion не Accepted. Coordinator проверяет full actual diff/inventory,
   checks/evidence/fingerprint и runtime/process observations до предъявления.

Текущий App каталог может не иметь stop/interrupt API. Тогда разрешенный
cooperative follow-up просит завершиться, но не удостоверяет остановку. Нужны
observed completed turn/resources и повторный fingerprint. Unknown writer дает
Blocked; archive/delete/handoff не заменяют stop/release. Worker не создает peer
или следующий ticket даже по переданному сообщению — возвращает запрос исходному
coordinator. Наблюдаемое нарушение блокирует продвижение, без auto-adoption.

## Durable review lifecycle и shared pools

Сначала coordinator наблюдает quiescence worker/resources и проверяет candidate
snapshot. Это evidence, еще не formal writer-release и не право нового writer.
`review-reserve {id,kind,candidate,quiescence}` под тем же exclusive transaction
lock связывает stable review_id с ticket/attempt/write-go/source/candidate/pools.
Atomic debit каждого applicable distinct pool предшествует reviewer side effect.
Только новый durable response `review_dispatch {id,binding_sha256}` разрешает
coordinator один reviewer launch. Helper reviewer/App APIs не вызывает.

`review-complete {id,binding_sha256,verdict,evidence,observation}` подтверждает
исходный reviewer и неизменный candidate, сохраняет actual verdict без нового
debit. Повторный reserve/completion того же ID отказывает без записи и grant.
Crash после reservation оставляет consumed budget и reserved proof; status/resume
не регенерируют launch. Unknown outcome требует reconciliation исходного reviewer,
не нового запуска; reserved/FAILED/CHANGES_REQUESTED не закрывают review gate.

Исполнимый порядок: observed quiescence + checked candidate → reserve → reviewer
→ complete → result с completed review ID → formal writer-release → await.
Receipt.review содержит id/verdict/evidence/findings. Для required review guard
принимает только completed APPROVED exact source/result/write-go/attempt binding.
CHANGES_REQUESTED оформляется как unaccepted result/release/Blocked; новое bounded
fix write-go отзывает прежние result/release, новый candidate требует нового ID.
После formal release событие result уже запрещено. Independent review не заменяет
приемку владельца и не удостоверяет реальные runtime observations автоматически.

Budgets принадлежат stable `RB-Txx` pools исходных boundaries. ticket_pools хранит
deduplicated ссылки: split делит counters, merge/repeated transfer объединяет
ссылки, не allowance. Новый receiving ID не создает pool. Reservation проверяет
все pools до debit; `full` требует доступного full pass, `fix` — прежнего full
review и доступного fix allowance каждого pool. Exhaustion/несовместимые merged
pools — Blocked/owner decision без implicit increase. Пределы review остаются
по independent-review; helper не добавляет новую policy matrix.

## Перенос, ревизия и scoped reuse

`revise`/`transfer` получают plan, moves, dependency/stage/gate remaps, reuse и
decision, привязанный ко всему old/new plan change. Transfer дополнительно имеет
mode partial/defer. Stable IDs сохраняются; новый receiving ticket содержит только
явно переданные AC. Каждый old required ticket AC либо unchanged, либо имеет
один source move `{from:{ticket,ac},to:{ticket,ac}}` к existing required receiving
AC со всеми прежними feature links. Many-to-one сохраняет каждый source mapping;
одного union(feature AC) недостаточно. Source AC остается optional history.
Partial оставляет собственные required AC, Deferred переносит все и снимает
source с required membership. Receiving scope/контракт получает fresh revision.

Каждый changed dependency/stage и removed/moved gate требует explicit remap с
evidence новой ready boundary. Producer obligations сохраняются, partial producer
не заменяет прежний полный prerequisite молча. Final gate остается final gate.
Пустые required stages запрещены; перенос в другую стадию требует явного
перестроения стадий/gates в валидный план. Оригинальные plans/decisions/receipts
сохраняются, affected approvals устаревают, gate proofs требуют нового plan hash.

Queue satisfaction отдельно допускает validated Deferred; technical readiness
требует Accepted producers. Stage/final completion также требует Accepted actual
required owners, gates и всех live obligations. Deferred сам не Accepted.
Transfer не advance: current остается до отдельного решения; revision может
rewind к более раннему stale predecessor, но не запускает следующий чат.

Whole spec/ADR hash меняет source identity всех tickets. Для unchanged Accepted
predecessor coordinator может передать explicit scoped reuse: original
attempt/plan/source/receipt/result/release hashes, target plan, observed snapshot,
verified archived sources и semantic evidence. Guard сравнивает неизменный ticket
contract/AC/dependencies/stage/workspace и declared spec/ADR bytes (offsets могут
сдвинуться), проверяет historical acceptance/review/release и сохранность всех
файлов, измененных тем attempt. Архив сохраняет original hash; старый REF/receipt/
owner decision не retarget-ится. Source/result drift, affected scope или отсутствие
proof дают fail-closed invalidation/new attempt. Полнота declared sections и
смысл «изменение не влияет» остаются attestation coordinator, не анализ prose
guard-ом. Latest writer result проверяется отдельно от intermediate old snapshots.

Existing self-check вызывает real CLI в disposable roots с cleanup. Scripted
App/role outcomes и actor/path/capability trace показывают только заданный protocol;
они не доказывают фактическое исполнение skill агентом, реальные App permissions/
recovery или физическую остановку writers. Live normal/failure/singleton gate —
отдельная приемка T06; static/scripted PASS его не закрывает.
