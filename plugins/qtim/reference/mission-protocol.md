# Mission protocol qtim для Codex

Канон App-first cross-dialog orchestration для `$qtim-mission`: read-only и
isolated writer nodes, optional node-local lazy team, topological integration,
clean-context verification, bounded fixes и recoverable portable state.

## Surface и activation

Full mode работает только когда callable surface текущей задачи предоставляет
project discovery, create/list/wait/read/rename peer tasks. Дополнительные
send/stop/handoff controls используются только после schema discovery.

| Режим | Условия | Действия |
|---|---|---|
| `AUTO-START` | явный запуск с Approved source или multi-peer shape + Approved spec + зелёный capability/git preflight | записать spec/runtime и создать ready nodes |
| `PREVIEW` | явный вызов, но source/graph/profile/target/budget требуют решения | показать Draft preview, не создавать tasks |
| `RECOMMEND` | topology найдена другим workflow | показать команду, ничего не запускать |

Цитата/quoted command, включая natural-language команду в одинарных,
типографских или двойных кавычках либо Markdown code span, вопрос,
пример, отрицание/исключение execution или mission-coordination (`не проводи как
миссию`, `не пользуйся/без использования qtim-миссии`, `это не qtim-миссия`) и
отложенное намерение (`не сейчас`, `завтра`,
`через час/неделю`, `по завершении`, `как только`, `после подтверждения/релиза`,
`если/когда наступит условие`, `при условии`, `в случае если`,
`через N секунд/полчаса/пару минут/сутки`),
feature completion и
SessionStart advisory — no-op. Точный ответ «Запускай предложенное» разрешает
старт только как referential approval непосредственно предшествующего полного
Approved mission preview; feature recommendation сама по себе таким preview не
является. Любой одиночный, fullwidth или незакрытый quote/code marker тоже
fail-closed: parser не угадывает, где заканчивается цитата.
Implicit skill loading включает лишь fail-closed classifier, не authorization.
`status | resume | stop` требуют отдельной явной команды.

## Mission preview

До первого task creation покажи как минимум:

```yaml
missionId: payments-contract
source: docs/features/payments/plan.md
sourceStatus: Approved
baseRevision: <sha>
integrationTarget: codex/qtim-mission-payments-contract
status: Approved
acceptanceCriteria: [...]
globalVerification: [...]
budgets: {taskRetries: 1, fixNodes: 2, verificationRetries: 2}
nodes:
  - id: contract
    dependsOn: []
    edgeContract: evidence
    execution: lazy
    lazy:
      leadProfile: {model: gpt-6-astra, reasoning: ultra}
      approvedIn: mission-preview
      rolePolicy: minimum-sufficient
      allowedRoles: [qtim-architect, qtim-testing]
    writePolicy: read-only
  - id: implementation
    dependsOn: [contract]
    edgeContract: integrated
    execution: direct
    writePolicy: isolated-worktree-writer
    writeScope: [plugins/qtim/reference/example.md]
terminalVerifier:
    id: final-verification
    dependsOn: [contract, implementation]
    execution: direct
    writePolicy: read-only
```

До создания path/ref/marker проверь: `slug == missionId`; mission/node ids имеют
единственную grammar lowercase ASCII kebab
<code>[a-z0-9]&#40;[a-z0-9-]*[a-z0-9]&#41;?</code> длиной 1–64;
separators, colon, dot/control,
option forms и aliases запрещены; node ids и производные
`qtim:<missionId>:<nodeId>` уникальны. Только затем формируются portable/runtime
paths. State ref обязан точно равняться
`refs/heads/codex/qtim-mission-state-<slug>`, integration target — отдельный
canonical `refs/heads/*`; оба проходят `git check-ref-format`. Integration target
не может занимать/D/F-conflict-ить с reserved state namespace.

Проверь минимум две content nodes, отсутствие unknown/self/cyclic edges, один
bounded outcome на node, canonical safe
repo-relative scopes единым parser для writer/lazy/spec и их пересечения после
нормализации; raw backslashes, drive/UNC/RFC3986 scheme, ASCII/Unicode controls,
basic/extended globs, `$HOME`/`%USERPROFILE%`/`~user`, component-wise
case-folded `.git` и trailing-dot aliases, Windows reserved
`CON/PRN/AUX/NUL/COM1..9/LPT1..9`, traversal и option-like paths запрещены.
Затем проверь
конечные budgets.
`terminalVerifier.dependsOn` должен в точности равняться множеству всех required
content nodes; пустой или частичный список запрещён. `terminalVerifier` —
отдельный reserved gate, не обычная content node: general ready scheduler его не
создаёт. Edge-contract map — total exact map всех и только DAG edges; разрешены
только `evidence | integrated`. Overlapping writer scopes требуют прямой
`integrated` edge. NFC/case-fold aliases считаются overlap.

## Capability и git preflight

1. Проверить main profile `gpt-6-astra` + `ultra`, если metadata видима.
2. Однозначно разрешить App project и сохранить opaque `projectId`.
3. Проверить точные schemas `create_thread`, `list_threads`, `wait_threads`,
   `read_thread`, rename и доступные follow-up/stop tools.
4. Зафиксировать source snapshot. Для git writer mode — base SHA, Approved
   integration branch, отдельный clean coordinator-owned integration worktree и
   clean state branch/worktree `codex/qtim-mission-state-<slug>`. State worktree
   меняет только `memory/missions/<slug>/`; каждый подтверждённый transition
   получает sequence + scoped checkpoint commit до следующего external side
   effect. Portable evidence никогда не пишется в integration worktree и не
   меняет content `expectedBase`. Частичный uncommitted state после crash
   блокирует resume; auto-stash/auto-commit/best-guess запрещены.
5. Git writer nodes используют `target.kind=worktree`: App создаёт detached
   checkout от exact Approved source state без shared writer ref. До edits node
   подтверждает пустой `git symbolic-ref -q HEAD` и exact `HEAD == expectedBase`;
   coordinator сверяет shared refs до/после create.
   Read-only git nodes используют resolved current project как `target.kind=local`,
   чтобы App не создавал неизвестный shared ref; worktree допустим только при
   подтверждённом detached exact revision. Non-git read-only использует local
   target; multi-writer non-git mission блокируется.
6. Portable path `memory/missions/<slug>/` writable вне integration worktree.
   Runtime registry разрешён только если `.codex/qtim-runtime/` надёжно
   gitignored и coordinator может доказать exclusive adjacent ownership lock,
   повторное чтение generation под lock и file
   `fsync + atomic replace + parent-directory fsync`.
   Paths детерминированы mission slug: registry `<slug>.json`, ownership lock
   `<slug>.ownership.lock`, promotion lock `<slug>.promotion.lock` в одном
   guarded `missions/` directory. Promotion lock хранит exact owner token,
   generation и integration target; caller-chosen альтернативный lock запрещён.
   До raw baseline registry уже существует, final-read ownership совпадает с
   coordinator + generation. Во время node допускается только exact
   before/after fingerprint canonical registry file текущей mission из
   coordinator-owned transition journal; после повторного JSON read validator
   маскирует только этот file entry. Parent directories, sibling runtime files
   и foreign registries остаются frozen.
7. Любая неоднозначность переводит запуск в `PREVIEW`.

## Два уровня orchestration

```text
mission coordinator
└─ peer node lead
   └─ local qtim subagents только при execution: lazy
```

Coordinator владеет DAG/integration/final gate. Direct node использует
`configured default` без model override. Lazy node lead получает Astra/Ultra только после exact
approval в spec, вызывает `$qtim-team-lazy` в mission-child mode, выбирает
minimum-sufficient roles с concrete responsibilities и возвращает один receipt.
Local agents работают waves по фактическому cap и не создают descendants. Настоящая
feedback loop возвращается как `ESCALATION_REQUEST`.

## Scheduler и asynchronous creation

1. `ready` означает: evidence edges ведут от `validated`, code edges — от
   `integrated`.
2. Перед созданием writer attempt зафиксировать `expectedBase`: mission base для
   root writer либо текущий HEAD Approved integration branch после всех её
   integrated dependencies. Worker до edits проверяет exact HEAD; mismatch =
   `BLOCKED`, не implicit rebase.
3. Создать принятые runtime ready nodes; overflow оставить `ready` до следующей
   wave. Plugin hard cap не вводится.
4. Writer task создаётся только с preflight-only prompt и запретом edits/commit.
   Она возвращает `WRITER PREFLIGHT READY` после detached exact base, clean
   including untracked и unchanged refs. Coordinator reconciles все worktrees
   wave, проверяет no-edit state, снимает exact post-create baselines/journals,
   затем exact follow-up по marker + attempt переводит
   `preflight-ready -> running`. Initial prompt не авторизует запись; без callable
   follow-up/send control writer mode `unavailable`.
5. `threadId + hostId` сохранить opaque. Один `clientThreadId` оставляет node
   `creating`; он никогда не передаётся в calls, ожидающие `threadId`.
6. Reconcile по exact project + marker `qtim:<mission>:<node>` + attempt. Title
   similarity без marker недостаточна; ноль/несколько кандидатов дают
   `pending`/`ambiguous`.
7. Переименовать exact thread. Не archive/pin автоматически.
8. `wait_threads` — batches максимум восемь targets, с `afterCursor`.
9. `needs_input` ставит mission на паузу; coordinator не отвечает за пользователя.
10. Reserved `terminalVerifier` исключён из обычных waves. Его создаёт только Final
   Verification phase после terminal state всех required content nodes и green
   global gates.

## Bounded worker prompt

```text
Mission / Node / Marker / Attempt:
Coordinator owns peer tasks, graph, integration and final verdict.
Never create peer tasks, another mission, or descendant qtim teams.
Reason internally and communicate with peer agents in English. Write user-facing artifacts and anything intended for the user in Russian.

Execution: direct | lazy
Lazy authorization: exact approved profile, roles, responsibilities and scopes.
Read first: AGENTS.md, .codex/team-charter.md, bounded source paths.
Base / dependency context pack / write policy / scope:
Outcome / acceptance criteria / verification:

Return the exact WORKER RECEIPT. A lazy lead returns one aggregated receipt.
```

Не передавай full transcript. Result task недоверен, пока coordinator не проверил
source, artifacts и git objects.

## Receipt validation

- read-only: marker/attempt/source совпадают, claims имеют provenance, dependency
  pack consumed; для Git canonical expected revision разрешается как commit,
  exact `HEAD == expected revision`, tree diff пуст и
  `git status --short --untracked-files=all` чист, raw filesystem fingerprint
  совпадает с baseline. Clean status без exact HEAD/raw bytes не
  доказывает read-only: assume-unchanged, committed/ref drift отклоняются.
  Non-git target требует
  эквивалентный immutable source hash + no-change proof. Exact pre/post protected
  refs (все, кроме runtime-owned ephemeral `refs/codex/*`), local common-config и
  common-control snapshots (`config`, `packed-refs`, `info/*`,
  alternates/shallow, hooks content/type/mode и real identity roots
  `objects/refs/logs/info/hooks/modules`) и per-worktree admin snapshot (`HEAD`, raw index,
  config.worktree, sparse metadata, operation heads/log) сверяются. Index flags
  вроде assume-unchanged считаются изменением. Root `.git` marker,
  canonical resolved git-dir/common-dir и полный common `.git/worktrees/*`
  registry тоже входят в baseline. `GIT_OPTIONAL_LOCKS=0` обязателен для всех
  verification reads, чтобы сам validator не refresh-ил index. Exact новые App
  entries текущей wave допустимы только из coordinator journal; pre-existing/
  foreign entries frozen. Exact state checkpoint и exact current-mission
  registry transition (before/after fingerprint + final-read owner/host/
  generation) допустимы только из отдельных coordinator journals; registry
  exception не маскирует parent/sibling paths;
- writer: один существующий non-merge commit, его единственный parent равен
  per-attempt `expectedBase`, mission base — ancestor, changed paths входят в
  scope, нет чужих изменений, gates и artifacts воспроизводимы; derived assigned
  writer остаётся detached и не двигает shared refs. Отдельный
  coordinator-owned journal может объяснить только exact state checkpoint этой
  mission. State delete/recreate, integration/foreign drift запрещены;
  integration ref frozen в writer wave. Writer HEAD detached и равен commit,
  worktree clean including untracked, raw filesystem
  соответствует commit tree, target scopes contained без symlink/junction,
  common Git config/control неизменны. Post-create baseline связывает exact
  `.git` marker, git-dir/common-dir, assigned common-worktree entry и всю wave:
  у assigned entries меняются только canonical `HEAD`/index и optional
  reflog/commit-message paths, а `config.worktree`, sparse/operation metadata,
  foreign и extra admin files frozen. Assigned admin files real,
  non-executable, single-link; index exact match commit без assume-unchanged,
  skip-worktree или unmerged stages. Submodule initialized/uninitialized topology
  плюс nested admin identity, worktree control, common config/control/hooks/
  packed-refs равны coordinator baseline, кроме заранее авторизованного scoped
  submodule transition. Каждый regular writer content file single-link;
- lazy: каждая local role имеет responsibility/output и explicit
  `write_policy: writer | read-only`; writer имеет непустые canonical
  `write_scopes`, read-only — ровно пустые `write_scopes: []` и явные canonical
  `read_scopes`; scopes не конфликтуют, ни один falsey scope не отбрасывается,
  node lead реально проверил reports, descendants не создавались. Coordinator
  передаёт exact responsibility/output/policy/scopes отдельно от receipt;
  self-reported allowlist не авторизует роль.

Raw filesystem snapshot до fan-out включает type, full mode, device, inode,
link count и bytes; он ограничен 50 000 entries и 512 MiB regular-file bytes.
Превышение либо FIFO/socket/device блокирует mission fail-closed.

Feedback loop, product fork, новая роль или scope overlap — не успешный receipt:
обязательны `status: BLOCKED` и `ESCALATION_REQUEST`; такой receipt запрещено
переводить `succeeded -> validated`. И наоборот, любой `ESCALATION_REQUEST`
требует `BLOCKED`, поэтому marker в `SUCCEEDED` receipt никогда не валидируется.

`succeeded` не разблокирует downstream. Только coordinator переводит
`succeeded -> validated` и пишет bounded summary в `receipts.md`.

## Dependency handoff

Context pack содержит validated outcome, source/commit/artifact ids, изменившиеся
contracts, invariants, blockers, forbidden interpretations и downstream criteria.
Source/base drift делает receipt `stale`.

## Code integration

1. Worker возвращает ровно один bounded commit из отдельного worktree.
2. Coordinator проверяет commit receipt.
3. От exact текущего Approved HEAD создаётся disposable detached transaction
   worktree без shared transaction ref; coordinator-managed `git cherry-pick`
   выполняется там и строго в topological order.
   `handoff_thread` не используется как DAG merge.
4. Affected gate выполняется в transaction worktree. Green gate разрешает fenced
   compare-and-swap promotion только из clean integration worktree: revisions
   должны быть canonical full 40/64-hex commits; под exclusive adjacent promotion
   lock повторно проверяются canonical Approved target ref, exact
   `symbolic-ref -q HEAD == refs/heads/<Approved target>`, exact old target/HEAD
   и ff-only ancestry; затем выполняется атомарный
   `update-ref <Approved target ref> <transaction> <expected-old>`, exact
   transaction tree sync и независимая проверка target ref + HEAD + clean
   status. Detached/wrong-branch worktree отклоняется. Ошибка после CAS требует
   доказанного rollback exact target ref/tree, иначе состояние `ambiguous`.
   Dirty state, занятый lock или drift блокируют promotion. Только
   подтверждённый promotion даёт `integrated`.
5. Red gate не продвигает Approved branch и даёт fail-visible `blocked`. На
   конфликте незавершённый cherry-pick abort-ится в transaction worktree.
   Conflict/fix node создаётся только после явного обновления graph/spec; force
   overwrite запрещён.

## Final verification и fixes

После всех обязательных nodes coordinator запускает global gates и фиксирует
integrated revision. Отдельная clean-context read-only peer task получает только
criteria, diff/revision, validated receipts и evidence и возвращает:

```text
MISSION VERIFICATION
mission:
integrated revision:
verdict: APPROVED | NOT APPROVED
criteria checked:
dependency claims checked:
confirmed findings:
rejected claims:
missing evidence:
verification commands/results:
```

Поле означает одну exact full-line запись: `verdict: APPROVED` или
`verdict: NOT APPROVED`, а не substring-шаблон. Indentation, tab, лишний пробел
или suffix (`APPROVED-ish`) отклоняется; после colon допустим ровно один ASCII
space. Если exact записей несколько, итоговой считается последняя.

Coordinator source-checks каждый finding. Подтверждённый `NOT APPROVED` может
создать bounded fix node только внутри Approved fix budget и после обновления
graph; затем affected gates и clean verifier повторяются. Exhausted budget =
`Blocked`. После `APPROVED` последний clean state checkpoint доставляется одним
scoped portable-evidence bundle commit через тот же transaction gate/fenced
promotion. После подтверждения exact promoted subtree coordinator создаёт
следующий clean scoped state checkpoint с `status: Done`, новым `stateSequence`
и `deliveredEvidenceRevision`. Revision — непустой canonical 40/64-hex Git
object id, равный promoted HEAD и разрешающийся как commit. Это единственный
durable переход в `Done`; promoted HEAD читается независимо после fenced
promotion, обе revisions разрешаются как commits и сравниваются exact.
Crash между promotion и checkpoint остаётся `Verifying`; `resume` сверяет
revision/subtree и идемпотентно дописывает checkpoint, а mismatch блокирует
reconciliation.

## Status, resume, stop и fallback

- До первого registry/portable write missing parents создаются от exact real
  root по одному component с lstat/realpath/same-filesystem revalidation после
  exclusive create или `already exists`; unverified recursive `mkdir -p`
  запрещён. Initial registry публикуется под canonical ownership lock через
  exclusive adjacent temp, file fsync, atomic no-clobber publication,
  parent-directory fsync и exact final read. Collision даёт `ambiguous`, а
  недоказанный host primitive — `unavailable`;
- `status`: portable DAG + проверенные runtime hints + следующий gate, без fan-out;
- `resume`: сначала подтвердить coordinator ownership. Same owner обязан видеть
  ту же generation. Для другого coordinator явный resume требует доказать, что
  прежний owner не running, затем получить exclusive ownership lock, повторно
  проверить generation, выполнить file
  `fsync + atomic replace + parent-directory fsync` и перечитать registry.
  Final read выполняется до снятия ownership lock и требует exact regular
  single-link file с mission/new owner/host/`generation == n+1`.
  Занятый/непроверяемый lock не удалять автоматически. Live прежний owner =
  `ambiguous`, непроверяемый =
  `unavailable`, generation drift = `stale`. Dirty state worktree или
  не-монотонный checkpoint sequence = `blocked` до explicit reconciliation.
  Только после ownership gate продолжать exact `live` nodes;
  pending/stale/orphan/ambiguous/unavailable/blocked показывать как blocker.
  Respawn — новая attempt в budget;
- `stop`: не создавать nodes, отправить stop только exact live threads если tool
  доступен, записать `Stopped`; не удалять tasks/worktrees/evidence;
- archive/delete/cleanup: отдельное подтверждение;
- нет peer tools: `$qtim-team-up` single-task fallback;
- dirty checkout, non-git writers, lost handle, changed base или conflict:
  fail-visible pause, не best guess.

Promotion всегда получает locks в порядке `ownership -> promotion` и перечитывает
registry owner/generation под обоими locks непосредственно перед ref CAS.
Занятый ownership lock или generation takeover блокирует promotion без ref move.

`SessionStart` — bounded passive scan: максимум 50 portable candidates, максимум
5 видимых records и `+more`. Для portable `Verifying` hook читает exact derived
state ref и не показывает mission, если authoritative checkpoint уже `Done`;
terminal checkpoint не доставляется повторно в Approved branch.
