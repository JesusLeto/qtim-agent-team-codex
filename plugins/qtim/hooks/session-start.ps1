$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

try { $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { $payload = $null }
$root = if ($payload -and $payload.cwd) { [string]$payload.cwd } else { [Environment]::CurrentDirectory }
while (-not (Test-Path -LiteralPath (Join-Path $root ".git"))) {
  $parent = Split-Path -Parent $root
  if (-not $parent -or $parent -eq $root) { break }
  $root = $parent
}
$charter = Join-Path $root ".codex/team-charter.md"
if (-not (Test-Path -LiteralPath $charter -PathType Leaf)) { exit 0 }
$match = Select-String -LiteralPath $charter -Pattern "qtim-version:\s*([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)" |
  Select-Object -First 1
$version = if ($match) { "v" + $match.Matches[0].Groups[1].Value } else { "legacy" }
$message = 'Команда Codex-агентов настроена. $qtim-feature — интервью/спецификация/review/approval/handoff, $qtim-mission — App mission/status/resume/stop, $qtim-team-up — эпик, $qtim-team-lazy — точечная задача, $qtim-update — обновить.'
Write-Output ("[qtim {0}] {1}" -f $version, $message)

$missionRoot = Join-Path $root "memory/missions"
if (-not (Test-Path -LiteralPath $missionRoot -PathType Container)) { exit 0 }
$unfinished = @()
$candidates = @(Get-ChildItem -LiteralPath $missionRoot -Directory -ErrorAction SilentlyContinue |
    Select-Object -First 51)
$capped = $candidates.Count -gt 50
foreach ($missionDir in @($candidates | Select-Object -First 50 | Sort-Object Name)) {
    if ($missionDir.Name.Length -gt 64 -or
        $missionDir.Name -notmatch '^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$') { continue }
    $missionFile = Join-Path $missionDir.FullName "mission.md"
    if (-not (Test-Path -LiteralPath $missionFile -PathType Leaf)) { continue }
    $statusMatch = Select-String -LiteralPath $missionFile -Pattern '^(?:\*\*)?(?:Status|Статус)(?:\*\*)?:\s*(.+?)\s*$' |
      Select-Object -First 1
    if (-not $statusMatch) { continue }
    $status = $statusMatch.Matches[0].Groups[1].Value.Trim()
    if ($status -match '^(?i:Draft|Approved|Running|Blocked|Verifying|Needs[- ]input)$') {
      if ($status -match '^(?i:Verifying)$') {
        $stateRef = "refs/heads/codex/qtim-mission-state-" + $missionDir.Name
        $statePath = "memory/missions/" + $missionDir.Name + "/mission.md"
        $stateText = @(& git -C $root show ("{0}:{1}" -f $stateRef, $statePath) 2>$null)
        if ($LASTEXITCODE -eq 0) {
          $stateMatch = $stateText | Select-String -Pattern '^(?:\*\*)?(?:Status|Статус)(?:\*\*)?:\s*(.+?)\s*$' |
            Select-Object -First 1
          if ($stateMatch -and
              $stateMatch.Matches[0].Groups[1].Value.Trim() -match '^(?i:Done)$') {
            continue
          }
        }
      }
      $unfinished += [PSCustomObject]@{ Slug = $missionDir.Name; Status = $status }
    }
}

if ($unfinished.Count -gt 0 -or $capped) {
  $visible = @($unfinished | Select-Object -First 5 | ForEach-Object {
    "{0}:{1}" -f $_.Slug, $_.Status
  })
  if ($unfinished.Count -gt 5) { $visible += "+$($unfinished.Count - 5)" }
  if ($capped) { $visible += "+more" }
  Write-Output (
    '[qtim mission advisory] Незавершённые: {0}. Ничего не запущено; продолжение только через $qtim-mission, resume <slug>.' -f
    ($visible -join ', ')
  )
}
