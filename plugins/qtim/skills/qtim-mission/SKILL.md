---
name: qtim-mission
description: "Use only when the user explicitly asks to start, preview, inspect, resume, status, or stop a qtim cross-dialog mission: coordinate visible Codex App tasks as a validated DAG, optionally run a bounded node-local lazy team, integrate isolated writer commits, and finish through a clean-context verification gate."
---

# qtim Mission

Координируй видимые peer-задачи Codex App как одну mission. Skill поддерживает
read-only и writer nodes, node-local `$qtim-team-lazy`, topological commit
integration, bounded fix loop и `status | resume | stop`.

Вызов skill разрешает только действия утверждённого mission graph. Coordinator
владеет peer tasks, DAG, runtime registry, integration и итоговым verdict. Node
lead не создаёт peer tasks или новую mission; local subagents не делегируют дальше.

## Activation Gate

Классифицируй запрос до любых external writes:

- `AUTO-START` — пользователь явно назвал `$qtim-mission` с глаголом исполнения
  и сослался на Approved/утверждённый source либо описал несколько отдельных
  Codex peer tasks; или недвусмысленно попросил создать несколько отдельных Codex
  задач/диалогов и провести их как одну qtim mission; source/spec `Approved`,
  DAG и budgets однозначны, capability/git preflight зелёный. Точный ответ
  «Запускай предложенное» также считается явным запуском, но только когда он
  отвечает на непосредственно предшествующий полный Approved mission preview
  с base/targets/scopes/budgets/gates в этом же контексте; одна лишь feature
  recommendation не считается таким preview;
- `PREVIEW` — mission вызвана явно, но цель сырая, approval отсутствует, граф,
  lazy profile, integration target, budget или preflight требуют решения;
  planning/evaluation-only формулировка (`только спланируй`, `составь план`,
  `оцени`, `проанализируй`) также всегда остаётся `PREVIEW` без peer tasks;
- `RECOMMEND` — другой workflow обнаружил mission-shaped topology.

Только `AUTO-START` вызывает `create_thread`. В `PREVIEW` покажи полный spec и
дождись approval. В `RECOMMEND` покажи topology и готовую команду, ничего не
создавай. Цитата или quoted command, вопрос о skill, документация, любое
отрицание/исключение execution или самой mission-coordination (`не запусти`,
`не проводи их как миссию`, `не пользуйся/без использования qtim-миссии`,
`это не qtim-миссия`, `кроме $qtim-mission`) и
отложенное намерение (`не сейчас`, `завтра`, `через час`, `после подтверждения`,
`через неделю`, `по завершении`, `как только`, `после релиза`,
`если/когда наступит условие`, `при условии`, `в случае если`,
`через N секунд/полчаса/пару минут/сутки`)
не являются affirmative executable intent и не дают `AUTO-START`. Любой quote
marker, включая одинарный/типографский/fullwidth, или Markdown code marker вокруг
natural-language mission-команды, включая пустую или незакрытую quote/code пару, так же
fail-closed, как quoted `$qtim-mission`. То же относится к размеру `L/XL`, одной
обычной задаче/диалогу, завершению `$qtim-feature` и `SessionStart` advisory.
Implicit loading skill разрешено только для классификации этого gate и никогда
само по себе не даёт authorization.

`status`, `resume` и `stop` — отдельные явно запрошенные control operations. Они
не расширяют scope и сами по себе не разрешают новые nodes вне Approved graph.

## Preconditions

1. Проверь профиль main task, если runtime его показывает: требуется
   `gpt-6-astra` + `ultra`. Плагин не переключает уже открытую задачу скрыто.
2. Прочитай `AGENTS.md`, `.codex/team-charter.md`, `memory/MEMORY.md`, незавершённый
   `memory/missions/<slug>/mission.md` и указанный Approved artifact. Если charter
   отсутствует, предложи `$qtim-setup`.
3. Прочитай полностью:
   - `../../reference/mission-protocol.md`;
   - `../../reference/mission-receipt.md`;
   - `../../reference/mission-state-schema.md`;
   - `../../reference/runtime-compat.md`.
4. Через доступную tool discovery проверь точные schemas project/thread tools.
   Требуются аналоги `list_projects`, `create_thread`, `wait_threads`,
   `read_thread`, `list_threads`, `set_thread_title`; для recovery/follow-up —
   доступные send/stop controls. Для любой writer node callable send/follow-up
   control обязателен как write-authorization phase; без него writer mission
   `unavailable`. Не угадывай tool names и handles.
5. Если peer thread tools недоступны, останови full mode и честно предложи
   `$qtim-team-up` как single-task fallback. Не называй subagents peer-задачами.

## Preview And Preflight

1. Разреши текущий App project через `list_projects`, не только по похожему имени.
2. Построй portable spec: slug, цель, source/base revision, integration target,
   acceptance criteria, global gates, nodes, dependencies, read/write scopes,
   `execution: direct | lazy`, expected receipts, retry/fix budgets и stop
   conditions, плюс отдельный reserved `terminalVerifier`. Write policy
   фиксируется как `read-only` либо `isolated-worktree-writer`.
3. До построения path/ref/marker проверь единый identity contract:
   `slug == missionId`, mission и node ids — lowercase ASCII kebab
   <code>[a-z0-9]&#40;[a-z0-9-]*[a-z0-9]&#41;?</code> длиной 1–64,
   без separator/colon/dot/control,
   option forms и aliases; node ids уникальны. Только после этого формируй
   `memory/missions/<slug>/`, runtime JSON и marker
   `qtim:<missionId>:<nodeId>`. State ref обязан в точности равняться
   `refs/heads/codex/qtim-mission-state-<slug>`, integration target — отдельный
   canonical `refs/heads/*`; оба проходят `git check-ref-format`. Integration
   target не может занимать или D/F-conflict-ить с reserved state namespace.
4. Проверь существование dependencies и ацикличность DAG до
   первого `create_thread`. Минимум — две содержательные nodes; verifier не
   заменяет decomposition. `terminalVerifier.dependsOn` обязан быть точным
   множеством всех required content nodes, а не пустым или частичным списком.
   Edge-contract map обязан в точности покрывать все и только DAG edges;
   допустимы лишь `evidence | integrated`, missing/extra/unknown entries блокируют
   scheduler.
5. Для `execution: lazy` spec обязан явно утвердить `gpt-6-astra` + `ultra`,
   minimum-sufficient unique roles, concrete responsibilities, local write scopes и
   `escalation: return-to-mission-coordinator`. Иначе `PREVIEW`.
6. Для git writer nodes:
   - зафиксируй base SHA, Approved integration branch, отдельный
     coordinator-owned integration worktree и отдельную state branch/worktree
     `codex/qtim-mission-state-<slug>`. Оба worktree должны быть clean; dirty state
     блокирует writers до выбора пользователя, auto-stash запрещён;
   - state worktree может менять только `memory/missions/<slug>/`. Каждый
     подтверждённый transition/receipt получает монотонный sequence и scoped
     checkpoint commit до следующего external side effect. Crash recovery читает
     последний clean committed checkpoint; частичный uncommitted diff блокирует
     resume и никогда не коммитится автоматически;
   - portable evidence никогда не пишется в integration worktree и не меняет
     integration HEAD/`expectedBase` во время content DAG;
   - root writer получает mission base; для downstream writer после integrated
     dependencies зафиксируй текущий integration HEAD как per-attempt
     `expectedBase`;
   - каждая writer node получает отдельный App worktree, созданный от exact
     Approved source state, и до первой записи обязана подтвердить detached HEAD
     (`git symbolic-ref -q HEAD` пуст) и `HEAD == expectedBase`. App worktree не
     создаёт shared writer ref. Coordinator сверяет refs до/после create и
     снимает exact protected `for-each-ref`, raw
     filesystem type/mode/device/inode/link-count/bytes, local common-config,
     common-control, exact root `.git` marker + resolved git-dir/common-dir,
     per-worktree admin и весь common `.git/worktrees/*` baselines.
     Все verification Git reads выполняются с `GIT_OPTIONAL_LOCKS=0`, чтобы
     validator сам не refresh-ил index;
     runtime-owned ephemeral `refs/codex/*` исключаются из protected snapshot.
     Все остальные refs frozen, кроме точного state checkpoint текущей mission
     из coordinator-owned monotonic journal; worker receipt не может сам
     разрешить ref move. State ref нельзя удалить/создать заново; integration
     target frozen на всю активную writer wave;
   - scopes writer nodes не пересекаются либо direct dependency edge
     `integrated` явно сериализует пересечение. Все scopes сначала проверяются как canonical safe
     repo-relative paths единым parser для writer/lazy/spec и нормализуются;
     `./path`, `path/../other`, raw backslashes, drive/UNC/RFC3986 scheme,
     ASCII/Unicode control, basic/extended glob, `$HOME`/`%USERPROFILE%`/`~user`,
     component-wise case-folded `.git` и trailing-dot aliases, Windows
     `CON/PRN/AUX/NUL/COM1..9/LPT1..9`, option-like paths и traversal не обходят
     overlap gate. NFC/case-fold aliases считаются пересечением; перед стартом и
     в receipt каждый target scope разрешается относительно exact worktree и
     отклоняется при symlink/junction component или realpath escape.
   - raw filesystem proof имеет hard preflight budget: максимум 50 000 entries и
     512 MiB прочитанных regular-file bytes. Превышение или FIFO/socket/device
     блокирует fan-out fail-closed.
7. Non-git target допускает read-only mission. Несколько writer nodes без
   проверяемого commit/isolation contract блокируются.
8. Запиши/обнови portable evidence в state worktree и checkpoint-branch вне
   integration worktree. Opaque ids храни только в
   `.codex/qtim-runtime/missions/<slug>.json`; каталог должен быть исключён из Git.
   Registry содержит coordinator owner + generation. Takeover получает exclusive
   deterministic adjacent ownership lock
   `.codex/qtim-runtime/missions/<slug>.ownership.lock`, повторно читает
   generation под lock и пишет через
   file `fsync + atomic replace + parent-directory fsync`;
   существующий/непроверяемый lock блокирует takeover.
   Если ignore ownership, exclusive lock или atomic replace не доказаны на host,
   не создавай registry и пометь cross-session resume/takeover `unavailable`.
   При первой mission недостающие `.codex/qtim-runtime/missions/` и portable
   `memory/missions/<slug>/` создавай от exact real project/worktree root по
   одному component: после каждого exclusive `mkdir` или `already exists`
   повторяй lstat/realpath/same-filesystem guard. Не используй unverified
   recursive `mkdir -p`. Первый registry публикуй под canonical ownership lock:
   adjacent temp через exclusive create + file fsync, затем atomic no-clobber
   publication на `<slug>.json`, parent-directory fsync и exact final read.
   Existing registry или temp collision = `ambiguous`; никогда не replace.
   Если host не доказывает no-clobber primitive, registry init `unavailable`.
   Registry создаётся и final-read ownership подтверждается до raw baseline.
   Его единственный canonical file для текущей mission может измениться во время
   fan-out только по отдельному coordinator-owned registry-transition journal:
   exact before/after fingerprint, owner thread, host и generation. Validator
   маскирует только content-entry этого файла после повторного JSON read; parent
   directories, соседние runtime files и foreign registries остаются frozen.
   Git promotion использует другой deterministic adjacent lock
   `<slug>.promotion.lock` с owner token, generation и exact integration target;
   произвольный caller-chosen lock path запрещён.

## Scheduling And Worker Contract

1. Создавай только `ready` nodes: все dependency edge contracts выполнены
   (`validated` для evidence, `integrated` для code dependency). Reserved
   `terminalVerifier` не входит в обычные scheduler waves.
2. Запускай принятые runtime nodes waves без plugin hard cap. Один `wait_threads`
   call содержит не более восьми targets и использует сохранённые cursors.
3. Direct peer task не получает `model`/`thinking`: используй configured default.
   Только Approved lazy node получает exact `gpt-6-astra` + `ultra`.
4. Writer startup строго двухфазный. Initial prompt bounded и preflight-only:
   marker `qtim:<mission-id>:<node-id>`, attempt, base, target, запрет любых edits/
   commit и требование вернуть `WRITER PREFLIGHT READY` только после detached
   `HEAD == expectedBase`, clean including untracked и unchanged shared refs.
   Coordinator reconciles все targets wave, проверяет no-edit READY, снимает
   exact post-create baselines/journals и лишь затем exact follow-up по marker +
   attempt авторизует edits. До follow-up node остаётся `preflight-ready`.
   Если callable follow-up/send control отсутствует, writer mode fail-visible
   `unavailable`; initial prompt не может заранее авторизовать запись.
5. После writer authorization рабочий prompt bounded: marker
   `qtim:<mission-id>:<node-id>`, base, execution,
   dependency context pack, scope/write policy, criteria, gates, receipt schema и
   запрет descendants. Все initial/follow-up worker prompts и coordinator-to-peer
   сообщения пиши на English; user-facing artifacts и итог mission — на Russian.
   Для writer prompt требует проверить detached worktree
   (`git symbolic-ref -q HEAD` не возвращает ref) и
   `git rev-parse HEAD == expectedBase` до edits. Не передавай полный transcript.
6. Lazy node lead вызывает `$qtim-team-lazy` в mission-child mode, выбирает все и
   только нужные роли, выполняет их локальными waves и возвращает один
   агрегированный receipt. Feedback loop даёт `ESCALATION_REQUEST`, не
   node-local `$qtim-team-up`.
7. Если `create_thread` вернул `threadId`, сохрани его как opaque runtime handle.
   Один `clientThreadId` означает `creating`, не usable thread. Reconcile через
   `list_threads` по exact project + marker + attempt; ноль/несколько кандидатов —
   fail-visible `pending`/`ambiguous`.
8. Переименуй подтверждённую задачу в `qtim:<mission-id>:<node-id>`. Не архивируй
   и не pin tasks автоматически.
9. `needs_input` поднимает mission в `Needs input`. Не отвечай за пользователя в
   другой задаче и не подменяй approval.

## Receipt Validation And Integration

1. После completion прочитай bounded result и нужные outputs. Worker
   `SUCCEEDED` переводит node только в `succeeded`.
2. Проверь marker/attempt, claims по source, dependency inputs, scope, changed
   files и gates. Writer и lazy scopes проходят один canonical repo-relative
   parser до containment/overlap checks. Git read-only node обязана доказать
   immutable snapshot: canonical expected revision разрешается как commit,
   `HEAD == expected revision`, tree diff пуст,
   `git status --short --untracked-files=all` чист и raw filesystem fingerprint
   exact совпадает с coordinator baseline. Один лишь clean status
   недостаточен: assume-unchanged bytes, committed/ref drift отклоняют receipt.
   Non-git read-only target
   предъявляет эквивалентный immutable source hash + no-change proof. Кроме того,
   coordinator сравнивает protected `for-each-ref` (все refs, кроме
   runtime-owned ephemeral `refs/codex/*`), local common-config и common-control
   baselines (`config`, `packed-refs`, `info/*`, alternates/shallow, hooks
   content/type/mode и real identity roots `objects/refs/logs/info/hooks/modules`).
   Per-worktree Git admin baseline (`HEAD`, raw index, worktree config,
   sparse-checkout и operation heads/log) также exact неизменен: index flags
   вроде assume-unchanged являются side effect.
   Common `.git/worktrees/*` registry тоже frozen: coordinator journal может
   добавить только exact новые App entries текущей wave; pre-existing/foreign
   entries неизменны. Для exact registry текущей mission допускается только
   доказанный before/after transition с final-read owner + generation; любой
   соседний runtime path остаётся частью raw snapshot.
   Read-only node использует текущий resolved local project target без
   App-created branch; worktree target допустим только когда runtime подтверждает
   detached exact revision. Coordinator journal может объяснить лишь exact
   state checkpoint текущей mission; integration/foreign drift
   запрещён.
3. Writer receipt принимается только если:
   - commit существует, его единственный parent равен per-attempt `expectedBase`,
     а mission base остаётся ancestor;
   - это ровно один non-merge bounded commit поверх `expectedBase`;
   - changed paths входят в node write scope, чужих изменений нет;
   - writer остаётся detached, а shared protected refs не меняются;
     coordinator-owned journal, переданный validator отдельно от недоверенного
     receipt, может содержать только exact state checkpoint текущей mission.
     State delete/recreate, integration/foreign ref moves и незаписанные
     transitions запрещены;
   - coordinator post-create baseline связывает writer с exact `.git` marker,
     canonical git-dir/common-dir и известным common-worktree entry. В активной
     wave mutable только `HEAD`, canonical index и optional reflog/commit-message
     paths всех assigned entries; каждый target затем независимо проверяется.
     `config.worktree`, sparse metadata, operation heads и любые extra admin files
     frozen; assigned admin files real, non-executable и single-link;
   - index exact соответствует commit, не имеет assume-unchanged/skip-worktree/
     unmerged flags; initialized/uninitialized submodule topology и submodule
     admin identity, worktree control, nested common config/control/hooks/
     packed-refs совпадают с coordinator baseline, кроме заранее явно
     авторизованного scoped submodule transition;
   - writer `HEAD == commit`, worktree clean с untracked files, raw filesystem
     соответствует commit tree с Git clean filters/submodule semantics, target
     scopes contained без symlink/junction, каждый regular content file
     single-link, common Git config/control unchanged;
   - verification commands и artifacts подтверждены coordinator.
4. Для lazy receipt каждая роль обязана явно указать `write_policy: writer |
   read-only`. Writer имеет непустые canonical `write_scopes`; read-only имеет
   ровно пустые `write_scopes: []` и явные canonical `read_scopes`. Ни один
   falsey/нестроковый scope не отбрасывается — receipt отклоняется. Coordinator
   передаёт validator exact role responsibility/output/policy/read+write scopes
   и node scope отдельно от недоверенного receipt; self-reported allowlist не
   расширяет authorization.
5. Только после проверки переведи `succeeded -> validated` и запиши bounded
   summary в `receipts.md`.
   Receipt с feedback loop, product fork, новой ролью или scope overlap обязан
   иметь `status: BLOCKED` + `ESCALATION_REQUEST` и никогда не проходит этот
   transition. Обратное также обязательно: любой `ESCALATION_REQUEST`, даже без
   распознанной причины, требует `status: BLOCKED`; marker в `SUCCEEDED` receipt
   запрещён.
6. Для каждого validated writer создай disposable **detached** transaction
   worktree без shared transaction ref от exact текущего HEAD Approved
   integration branch. Выполни coordinator-managed
   `git cherry-pick` только там и строго в topological order. Native
   `handoff_thread` не является DAG integration primitive.
7. Запусти affected gate в transaction worktree. Green gate разрешает fenced
   promotion только из clean integration worktree: всегда бери canonical locks
   в порядке `ownership -> promotion`, перечитай exact owner + generation под
   обоими locks, потребуй canonical full 40/64-hex commit ids, затем повторно
   проверь `integration HEAD == expected old`, докажи ff-only ancestry и атомарно
   потребуй exact `symbolic-ref -q HEAD == refs/heads/<Approved target>` и
   выполни exact-old `update-ref` compare-and-swap именно над этим target ref.
   Затем синхронизируй worktree exact transaction tree и независимо подтверди
   target ref + `HEAD == transaction HEAD` плюс clean status; detached/wrong
   branch отклоняется, ошибка после CAS требует проверенного rollback target ref
   и tree, иначе состояние
   `ambiguous`. Это compare-and-swap semantics для всех mission
   coordinators; занятый/непроверяемый lock или drift блокирует promotion. Только
   после подтверждённого promotion выставь `integrated`. Red gate оставляет
   Approved branch неизменной и переводит node в fail-visible `blocked`, сохраняя
   receipt. При scope violation или
   конфликте integration останови; незавершённый cherry-pick abort-ится в
   transaction worktree, а conflict/fix node добавляй только через явное
   обновление Approved graph. Force overwrite запрещён.
8. Downstream получает только validated context pack и integrated commit ids.
   Изменение source/base делает прежний receipt stale.

## Final Verification And Fix Loop

1. После integration/validation всех обязательных nodes запусти global project
   gates и зафиксируй integrated revision.
2. Создай ровно одну отдельную clean-context read-only task из reserved
   `terminalVerifier`. Для verifier не задавай model/thinking без отдельного
   explicit Approved override.
3. Передай criteria, integrated diff/revision, validated receipts, gates и
   отклонённые claims. Verifier возвращает deterministic exact line
   `verdict: APPROVED` либо `verdict: NOT APPROVED`. Coordinator принимает только
   literal full-line records: без indentation, tabs, лишних пробелов или suffix;
   допустим ровно один ASCII space после colon. Последний exact verdict record
   является итоговым.
4. Coordinator проверяет каждый finding по фактическому source и записывает
   confirmed/rejected findings.
5. При `NOT APPROVED` создавай bounded fix node только когда owner/scope
   однозначны, finding подтверждён и fix budget не исчерпан. Обнови graph/spec до
   создания, затем повтори affected gates и clean verification.
6. Исчерпанный budget или новый продуктовый/необратимый выбор даёт `Blocked`.
7. Только подтверждённый `APPROVED` записывается последним marker в state
   `verification.md`. Создай из последнего clean state checkpoint один scoped
   portable-evidence bundle commit в transaction worktree от текущего Approved
   integration HEAD, прогони docs/state gate и продвинь его тем же fenced
   exact-old `--ff-only` protocol.
8. После подтверждённой доставки exact bundle запиши следующий монотонный clean
   state checkpoint: `status: Done`, новый `stateSequence` и exact
   `deliveredEvidenceRevision`. Revision должна быть canonical 40/64-hex object
   id, совпадать с независимо перечитанным promoted HEAD и обе revisions должны
   разрешаться Git как commit. Crash после
   promotion, но до этого checkpoint,
   остаётся `Verifying`: `resume` сверяет promoted subtree/revision и
   идемпотентно создаёт checkpoint один раз. Несовпадение revision/subtree =
   `Blocked`; уже совпавший `Done` checkpoint = no-op. Только этот durable
   post-delivery checkpoint завершает mission.

Final mission verification не заменяет ADR stress-test и risk-based independent
review, требуемые charter.

## Status, Resume, Stop

- `status <slug>` — прочитай portable state, проверь runtime hints через доступные
  tools и покажи DAG, revisions, live/blocked nodes и следующий gate; ничего не
  создавай;
- `resume <slug>` — сначала сверь coordinator ownership. Тот же exact owner
  продолжает только при совпавшей generation. Другой coordinator по явному
  `resume` обязан через thread tools подтвердить, что прежний owner не running;
  live owner даёт `ambiguous`, непроверяемый — `unavailable`. Только после
  exclusive ownership lock, повторного чтения generation под lock, file
  `fsync + atomic replace + parent-directory fsync` и финального чтения registry
  под тем же lock новый owner получает право fan-out/integration. Registry после
  replace обязан быть exact regular single-link file с mission/new owner/host/
  `generation == n+1`. Lock никогда не удаляется best-effort: stale/непроверяемый
  lock даёт `unavailable`. Затем сверь project, marker, attempt,
  thread/host, source/base, clean state worktree и монотонный checkpoint sequence.
  Продолжай только exact `live`; `pending | stale | orphan | ambiguous |
  unavailable | blocked` оставляй fail-visible. Dirty/не-монотонный state =
  `blocked` до explicit reconciliation. Respawn — новая
  attempt в пределах budget, не подмена потерянного handle;
- `stop <slug>` — прекрати новый fan-out, пометь running nodes `cancelled` или
  сохрани их last-known state, отправь bounded stop request только доступным exact
  threads, запиши `Stopped`. Не удаляй tasks, worktrees или portable evidence;
- cleanup/archive/delete — отдельное действие после отдельного подтверждения.

Plugin `SessionStart` advisory просматривает максимум 50 portable candidates,
показывает максимум 5 и `+more`; ничего не запускает. Для portable `Verifying`
он читает exact derived state ref и подавляет reminder при authoritative `Done`,
который намеренно не доставляется повторно в Approved branch.

`$qtim-team-down` может только зафиксировать handoff и закрыть известные local
subagent threads; mission lifecycle принадлежит `$qtim-mission`.

## Stop Conditions

Верни управление пользователю при permission/approval request, новом продуктовом
или необратимом выборе, dirty checkout, integration conflict, scope overlap,
invalid receipt, потерянном/неоднозначном handle, изменившемся base, исчерпанном
budget или необходимости расширить Approved scope.

## Anti-Patterns

- Создать все nodes сразу, игнорируя dependency validation/integration.
- Передать `clientThreadId` в tool, ожидающий `threadId`.
- Выдать `PREVIEW`, `RECOMMEND` или SessionStart advisory за authorization.
- Довериться `SUCCEEDED`, commit SHA или verifier finding без source-check.
- Передать downstream transcript или непроверенные claims.
- Использовать shared checkout для параллельных writers.
- Задать direct task model override без отдельного Approved выбора.
- Разрешить lazy node lead запустить team-up, peer task или descendants.
- Автоматически stash/force-resolve/archive/delete ради продолжения mission.
- Писать portable evidence в integration worktree или продвигать Approved branch
  до зелёного affected gate.
- Оставлять portable transitions только uncommitted либо смешивать state
  checkpoint commits с content `expectedBase` до финальной evidence delivery.
- Выполнять takeover при live/непроверяемом прежнем coordinator или без atomic
  generation compare-and-swap.
