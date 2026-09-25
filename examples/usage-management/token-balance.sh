#!/usr/bin/env bash
# OpenClaw quota-routing reference template; adapt and review before enabling writes.
# Assumes `openclaw models status` contains an "OpenAI usage" line with 5h/Week
# percentages and reset countdowns. Change the parser for your provider/runtime.
# Dry-run may still send a harmless real model probe when a transition is due.

set -euo pipefail

# Operator settings — replace agent IDs and verify both model routes/fallbacks.
THRESHOLD=${THRESHOLD:-15}
TRACK_5H=${TRACK_5H:-1}
TRACK_WEEK=${TRACK_WEEK:-1}
NORMAL_MODEL=${NORMAL_MODEL:-openai/gpt-6-luna}
ALTERNATE_MODEL=${ALTERNATE_MODEL:-anthropic/claude-sonnet-5}
FALLBACKS_NORMAL=${FALLBACKS_NORMAL:-'["anthropic/claude-sonnet-5","google/gemini-3.5-flash"]'}
FALLBACKS_ALTERNATE=${FALLBACKS_ALTERNATE:-'["google/gemini-3.5-flash"]'}
MANAGED_AGENTS=(agent-one agent-two) # Replace with exact IDs; omit excluded agents.
PROBE_AGENT=${PROBE_AGENT:-agent-one}
PROBE_SESSION=${PROBE_SESSION:-agent:agent-one:quota-probe}
SESSION_MANAGER_AGENT=${SESSION_MANAGER_AGENT:-agent-one}
SESSION_MANAGER_SESSION=${SESSION_MANAGER_SESSION:-agent:agent-one:quota-session-sweep}
APPLY=${APPLY:-0} # Dry-run default. Set APPLY=1 only after adapting and validating.

if [ "$THRESHOLD" -lt 1 ] || [ "$THRESHOLD" -gt 100 ] || { [ "$TRACK_5H" != 1 ] && [ "$TRACK_WEEK" != 1 ]; }; then
  printf 'Configure a 1–100 threshold and enable at least one trigger window.\n' >&2
  exit 2
fi
if [ "${MANAGED_AGENTS[*]}" = "agent-one agent-two" ]; then
  printf 'Replace the example MANAGED_AGENTS list before enabling this template.\n' >&2
  exit 2
fi

ROOT=${USAGE_ROUTING_DIR:-"$HOME/.openclaw/usage-routing"}
LOG="$ROOT/token-balance.log"
STATE="$ROOT/token-balance.state"
mkdir -p "$ROOT"
touch "$LOG"
log() { printf '%s | %s\n' "$(date -Is)" "$*" >>"$LOG"; }

# Prevent overlapping polls from racing the reset-latch state.
exec 9>"$ROOT/token-balance.lock"
flock -n 9 || { log "SKIP: another poll is active"; exit 0; }

state_get() {
  [ -f "$STATE" ] || return 0
  sed -n "s/^$1=//p" "$STATE" | tail -1
}
state_write() {
  local mode=$1 reset5=$2 resetWeek=$3 pending=$4 pendingModel=$5 tmp="$STATE.tmp.$$"
  umask 077
  printf 'mode=%s\nreset_5h_at=%s\nreset_week_at=%s\nsession_sweep_pending=%s\nsession_sweep_model=%s\n' \
    "$mode" "$reset5" "$resetWeek" "$pending" "$pendingModel" >"$tmp"
  mv -f "$tmp" "$STATE"
}

meter=$(timeout 90 openclaw models status 2>/dev/null) || {
  log "SKIP: usage status unavailable; no route change"
  exit 0
}

# Parse the example OpenClaw status format. Unselected windows return -1/0 and
# do not participate in decisions. Missing selected windows make the parse fail.
values=$(printf '%s\n' "$meter" | python3 -c '
import re, sys
line = next((s for s in sys.stdin.read().splitlines() if "openai usage:" in s.lower()), "")
track5, trackweek = sys.argv[1:3]
def window(label, enabled):
    if enabled != "1": return -1, 0
    m = re.search(r"\b" + label + r"\s+(\d+)%\s*left\s+⏱\s*((?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?(?:\s*(\d+)s)?)", line, re.I)
    if not m: raise ValueError(label)
    pct = int(m.group(1))
    d, h, minute, sec = (int(m.group(i) or 0) for i in range(3, 7))
    remaining = d*86400 + h*3600 + minute*60 + sec
    if pct > 100 or remaining <= 0: raise ValueError(label)
    return pct, remaining
try:
    a, b = window("5h", track5)
    c, d = window("Week", trackweek)
except ValueError:
    raise SystemExit(2)
print(a, b, c, d)
' "$TRACK_5H" "$TRACK_WEEK") || {
  log "SKIP: a selected usage window could not be parsed; no route change"
  exit 0
}
read -r P5 R5 PWeek RWeek <<<"$values"
NOW=$(date +%s)
NEXT5=$((NOW + R5))
NEXTWEEK=$((NOW + RWeek))

mode=$(state_get mode); [ -n "$mode" ] || mode=unknown
reset5=$(state_get reset_5h_at); [ -n "$reset5" ] || reset5=0
resetWeek=$(state_get reset_week_at); [ -n "$resetWeek" ] || resetWeek=0
pending=$(state_get session_sweep_pending); [ -n "$pending" ] || pending=0
pendingModel=$(state_get session_sweep_model)

low=0
if [ "$TRACK_5H" = 1 ] && [ "$P5" -lt "$THRESHOLD" ]; then low=1; [ "$reset5" -gt 0 ] || reset5=$NEXT5; fi
if [ "$TRACK_WEEK" = 1 ] && [ "$PWeek" -lt "$THRESHOLD" ]; then low=1; [ "$resetWeek" -gt 0 ] || resetWeek=$NEXTWEEK; fi
if [ "$TRACK_5H" = 1 ] && [ "$reset5" -gt 0 ] && [ "$NOW" -ge "$reset5" ] && [ "$P5" -ge "$THRESHOLD" ]; then reset5=0; fi
if [ "$TRACK_WEEK" = 1 ] && [ "$resetWeek" -gt 0 ] && [ "$NOW" -ge "$resetWeek" ] && [ "$PWeek" -ge "$THRESHOLD" ]; then resetWeek=0; fi

probe_route() {
  local model=$1 raw
  raw=$(timeout 180 openclaw agent --agent "$PROBE_AGENT" --model "$model" \
    --thinking minimal --session-key "$PROBE_SESSION" \
    --message 'Reply exactly MODEL_ROUTE_OK; do not use tools.' --json 2>&1) || return 1
  printf '%s' "$raw" | MODEL_WANT="$model" python3 -c '
import json, os, re, sys
s = sys.stdin.read(); m = re.search(r"\{", s)
if not m: raise SystemExit(1)
try: d = json.loads(s[m.start():])
except Exception: raise SystemExit(1)
r = d.get("result", {}); meta = r.get("meta", {}).get("agentMeta", {})
p = r.get("payloads", []); text = p[0].get("text", "") if p else ""
want = os.environ["MODEL_WANT"]; actual = meta.get("model")
ok = d.get("status") == "ok" and actual in (want, want.split("/", 1)[-1]) and text.strip() == "MODEL_ROUTE_OK"
raise SystemExit(0 if ok else 1)
'
}

apply_model() {
  local model=$1 fallbacks=$2 ops
  ops=$(python3 - "$model" "$fallbacks" "${MANAGED_AGENTS[@]}" <<'PY'
import json, sys
model, fallback_json, *agents = sys.argv[1:]
fallbacks = json.loads(fallback_json)
if not fallbacks: raise SystemExit("configure at least one valid fallback")
ops = [
 {"path":"agents.defaults.model.primary","value":model},
 {"path":"agents.defaults.model.fallbacks","value":fallbacks},
 {"path":"agents.defaults.subagents.model.primary","value":model},
 {"path":"agents.defaults.subagents.model.fallbacks","value":fallbacks},
]
for agent in agents:
    ops += [{"path":f"agents.entries.{agent}.model.primary","value":model},
            {"path":f"agents.entries.{agent}.model.fallbacks","value":fallbacks}]
print(json.dumps(ops, separators=(",", ":")))
PY
  )
  if [ "$APPLY" != 1 ]; then
    printf 'DRY_RUN: would set %s for %s named agents and global/subagent defaults\n' "$model" "${#MANAGED_AGENTS[@]}"
    return 2
  fi
  timeout 180 openclaw config set --batch-json "$ops" >>"$LOG" 2>&1
}

sweep_sessions() {
  local model=$1 message raw managed
  managed=$(IFS=,; printf '%s' "${MANAGED_AGENTS[*]}")
  message="Quota transition to ${model}. Managed agent IDs: ${managed}. Inventory their live/continuable sessions and active child sessions; patch only that declared scope, verify every session key, and return SESSION_SWEEP_OK checked=N expected=N exceptions=0 only if complete; otherwise return SESSION_SWEEP_PENDING with exceptions. Do not edit config or credentials."
  raw=$(timeout 600 openclaw agent --agent "$SESSION_MANAGER_AGENT" --model "$model" \
    --session-key "$SESSION_MANAGER_SESSION" --message "$message" --json 2>&1) || return 1
  printf '%s' "$raw" | grep -Eq 'SESSION_SWEEP_OK checked=[0-9]+ expected=[0-9]+ exceptions=0'
}

shouldAlternate=0
if [ "$low" = 1 ] || [ "$reset5" -gt 0 ] || [ "$resetWeek" -gt 0 ]; then shouldAlternate=1; fi
nextMode=normal; target=$NORMAL_MODEL; fallbacks=$FALLBACKS_NORMAL
if [ "$shouldAlternate" = 1 ]; then nextMode=alternate; target=$ALTERNATE_MODEL; fallbacks=$FALLBACKS_ALTERNATE; fi

if [ "$pending" = 1 ] && [ -n "$pendingModel" ] && [ "$APPLY" = 1 ]; then
  if sweep_sessions "$pendingModel"; then
    state_write "$mode" "$reset5" "$resetWeek" 0 "$pendingModel"
    log "SESSION_SWEEP_OK: pending session migration verified for $pendingModel"
    pending=0
  else
    log "SESSION_SWEEP_PENDING: retry later for $pendingModel"
  fi
fi

if [ "$nextMode" != "$mode" ]; then
  if ! probe_route "$target"; then log "BLOCKED: real route probe failed for $target"; exit 0; fi
  if apply_model "$target" "$fallbacks"; then
    state_write "$nextMode" "$reset5" "$resetWeek" 1 "$target"
    if sweep_sessions "$target"; then state_write "$nextMode" "$reset5" "$resetWeek" 0 "$target"
    else log "SESSION_SWEEP_PENDING: defaults changed; existing sessions need reconciliation"; fi
    log "TRANSITION_OK: mode=$nextMode target=$target"
  else
    rc=$?; [ "$rc" -eq 2 ] && log "DRY_RUN: transition not applied" || log "BLOCKED: config batch failed"
  fi
else
  if [ "$mode" = unknown ]; then state_write "$nextMode" "$reset5" "$resetWeek" 0 ""; fi
  if [ "$mode" = alternate ]; then state_write "$nextMode" "$reset5" "$resetWeek" "$pending" "$pendingModel"; fi
  log "NO_CHANGE: mode=$mode 5h=${P5}% week=${PWeek}%"
fi
