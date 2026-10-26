#!/bin/sh

root=${1:-}
if [ -z "$root" ]; then
  root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi

charter="$root/.codex/team-charter.md"
test -f "$charter" || exit 0

version=$(grep -m1 'qtim-version:' "$charter" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?' || true)
if [ -n "$version" ]; then
  version="v$version"
else
  version="legacy"
fi

message='Команда Codex-агентов настроена. $qtim-feature — интервью/спецификация/review/approval/handoff, $qtim-mission — App mission/status/resume/stop, $qtim-team-up — эпик, $qtim-team-lazy — точечная задача, $qtim-update — обновить.'
printf '[qtim %s] %s\n' "$version" "$message"

mission_root="$root/memory/missions"
test -d "$mission_root" || exit 0

find "$mission_root" -mindepth 2 -maxdepth 2 -type f -name mission.md -print 2>/dev/null |
  head -n 51 |
  (
    items=
    active=0
    inspected=0
    capped=0
    while IFS= read -r mission_file; do
      inspected=$((inspected + 1))
      if [ "$inspected" -gt 50 ]; then
        capped=1
        break
      fi
      slug=$(basename "$(dirname "$mission_file")")
      case "$slug" in
        ""|*[!a-z0-9-]*|-*|*-) continue ;;
      esac
      test "${#slug}" -le 64 || continue
      status_line=$(grep -i -m1 -E '^(\*\*)?(status|статус)(\*\*)?:[[:space:]]*' "$mission_file" || true)
      test -n "$status_line" || continue
      status=$(printf '%s\n' "$status_line" |
        sed -E 's/^(\*\*)?[Ss][Tt][Aa][Tt][Uu][Ss](\*\*)?:[[:space:]]*//; s/^(\*\*)?[Сс][Тт][Аа][Тт][Уу][Сс](\*\*)?:[[:space:]]*//; s/[[:space:]]+$//')
      normalized=$(printf '%s' "$status" | tr '[:upper:]' '[:lower:]')
      case "$normalized" in
        draft|approved|running|blocked|verifying|needs-input|"needs input") ;;
        *) continue ;;
      esac
      if [ "$normalized" = "verifying" ]; then
        state_ref="refs/heads/codex/qtim-mission-state-$slug"
        state_content=$(git -C "$root" show "$state_ref:memory/missions/$slug/mission.md" 2>/dev/null || true)
        state_status_line=$(printf '%s\n' "$state_content" |
          grep -i -m1 -E '^(\*\*)?(status|статус)(\*\*)?:[[:space:]]*' || true)
        state_status=$(printf '%s\n' "$state_status_line" |
          sed -E 's/^(\*\*)?[Ss][Tt][Aa][Tt][Uu][Ss](\*\*)?:[[:space:]]*//; s/^(\*\*)?[Сс][Тт][Аа][Тт][Уу][Сс](\*\*)?:[[:space:]]*//; s/[[:space:]]+$//' |
          tr '[:upper:]' '[:lower:]')
        test "$state_status" = "done" && continue
      fi
      active=$((active + 1))
      if [ "$active" -le 5 ]; then
        if [ -n "$items" ]; then
          items="$items, "
        fi
        items="${items}${slug}:${status}"
      fi
    done

    if [ "$active" -gt 0 ] || [ "$capped" -eq 1 ]; then
      if [ "$active" -gt 5 ]; then
        items="$items, +$((active - 5))"
      fi
      if [ "$capped" -eq 1 ]; then
        if [ -n "$items" ]; then
          items="$items, "
        fi
        items="${items}+more"
      fi
      printf '[qtim mission advisory] Незавершённые: %s. Ничего не запущено; продолжение только через $qtim-mission, resume <slug>.\n' "$items"
    fi
  )
