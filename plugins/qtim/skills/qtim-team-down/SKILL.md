---
name: qtim-team-down
description: Use when the user asks to finish or shut down the active qtim Codex team. Closes no-longer-needed subagent threads, records durable state in memory, and reports unfinished work honestly.
---

# qtim Team Down

In Codex there is no persistent team object on disk; "down" means close active agent threads and preserve useful state.

**Перед сворачиванием:** для завершённого эпика C/D запусти `$qtim-team-retro`,
если есть проверяемый новый урок. При отсутствии урока не создавай запись ради
ритуала. Retro не блокирует сворачивание незавершённого эпика.

## Steps

1. List the active qtim agent threads you have in current context.
2. Ask any running thread for a concise final status if needed.
3. Close completed or no-longer-needed threads when the close tool is available.
4. Перед записью в `memory/` или `docs/features/` открой `$qtim-kb-format`. Обнови только живые
   решения, открытые баги/блокеры и указатели на долговечные test artifacts.
   Закрытые проходы не дописывай в активные логи; архивируй лишь историю,
   которая нужна для будущего решения. При устаревшем evidence предложи
   `$qtim-kb-refresh`.
5. Эпик не завершён -> запиши `memory/epic-state.md` (его читает `$qtim-team-up` в новой сессии и предлагает продолжить):

   ```markdown
   # Epic state: <название эпика>
   Обновлено: <дата> · Фаза: design | impl | test | review
   ## Сделано
   ## В полёте (задача — роль — статус — следующий шаг)
   ## Открытые вопросы / блокеры
   ## Следующий шаг при продолжении
   ```

   Эпик завершён — **удали** устаревший `epic-state.md`, не оставляй ложного «в полёте».
6. Если связанная фича в `docs/features/<slug>/` действительно достигла `Done`
   по проверенной приёмке и есть evidence влития, получи решение владельца
   об архивации и очистке (учти уже данное в сессии). Только после него
   переведи фичу в `Archived` по `../../reference/feature-pipeline.md`:
   сохрани `prd.md`/`plan.md` или `feature-brief.md`, обнови существующий
   короткий итоговый указатель в `memory/decisions.md`, удали только
   идентифицированные как временные файлы `.work/`. Само сворачивание команды
   не доказывает `Done` и не разрешает удаление; без evidence или решения
   владельца сохрани статус `Done` и сообщи о незавершённой архивации.
7. Mark any unfinished work clearly in the visible plan or final report.
8. Tell the user what remains open and whether a new Codex task is recommended.

Если существует Running/Needs input/Blocked mission, не присваивай ей `Done` и не
поглощай её lifecycle. Запиши в portable handoff только slug, portable status,
blocker/следующий gate и команду `$qtim-mission, status|resume <slug>`. Exact task,
thread, host, cursor и worktree handles запрещено копировать в `memory/` или
другой portable artifact: они остаются только в gitignored runtime registry.
Закрывай только известные local subagent threads; peer mission tasks, worktrees,
runtime registry и portable evidence оставь `$qtim-mission`.

## Rules

- Do not delete `.codex/team-charter.md`, `.codex/agents`, hooks, or memory.
- Do not pretend an agent thread survived a restart if you no longer have its id.
- Do not leave important conclusions only in chat. Put durable project knowledge into `memory/`.
- Do not archive/delete peer mission tasks or rewrite mission status as part of team-down.
