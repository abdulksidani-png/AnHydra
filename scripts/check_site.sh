#!/usr/bin/env bash
# Is the live site actually working? Run this before a demo.
#
#   bash scripts/check_site.sh                      # checks https://anhydra.work
#   bash scripts/check_site.sh http://localhost:8000
#
# Checks reachability, that a model is loaded, that a real sequence scores, that the response
# carries every field the UI needs, and whether the explanation came from Gemini or the offline
# fallback. Exits non-zero if anything fails, so it can gate a deploy.

set -uo pipefail
BASE="${1:-https://anhydra.work}"
# Optional mode-0600 file containing Authorization: Bearer <API access token>.
# curl reads it directly, keeping the credential out of process arguments.
auth_args=()
if [[ -n "${AUTH_HEADER_FILE:-}" ]]; then
  auth_args=(-H "@$AUTH_HEADER_FILE")
fi
# Gly/Ser-rich toy: should score high. Known-good input, so a low score means something changed.
SEQ="MSGSGSGKEKEKDKDKGSGSGSHGHGSGSEKEKDKDKGSGSGSGHKGHGSGSEKEKDKDK"
fail=0

say()  { printf '%s\n' "$*"; }
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$*"; }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; fail=1; }
note() { printf '  ----  %s\n' "$*"; }

say "Checking $BASE"
say

# 1. Reachability + health -----------------------------------------------------------------------
health=$(curl -fsS --max-time 15 "$BASE/health" 2>/dev/null)
if [[ -z "$health" ]]; then
  bad "site unreachable (no response from $BASE/health)"
  say
  say "The site is down. On the server:  systemctl status tardiscreen caddy"
  exit 1
fi
ok "site reachable"

if python3 -c "import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get('model_trained') else 1)" \
     "$health" 2>/dev/null; then
  ok "model artifact is present (inference checked below)"
else
  bad "model artifact NOT present — /score will return 503"
  note "fix: python -m tardiscreen.model   (stop the service first if it gets Killed)"
fi

# A SPA fallback can return HTTP 200 HTML, so validate JSON as well as status.
readiness=$(curl -fsS --max-time 30 "$BASE/ready" 2>/dev/null)
if python3 -c "import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get('status') == 'ok' else 1)" \
     "$readiness" 2>/dev/null; then
  ok "model bundle and encoder runtime validated"
else
  bad "/ready failed or returned non-JSON; check API routing and model runtime"
fi

# 2. A real scoring request ----------------------------------------------------------------------
say
say "Scoring a known Gly/Ser-rich sequence (first request may take ~15s while ESM-2 loads)"
body=$(curl -fsS --max-time 120 -X POST "$BASE/score" \
         "${auth_args[@]}" \
         -H 'content-type: application/json' \
         -d "{\"sequence\":\"$SEQ\"}" 2>/dev/null)

if [[ -z "$body" ]]; then
  bad "/score failed; check AUTH_HEADER_FILE for an eligible API token and service readiness"
  say
  say "On the server:  journalctl -u tardiscreen -n 40 --no-pager"
  exit 1
fi
ok "/score responded"

# 3. Response shape and values -------------------------------------------------------------------
python3 - "$body" <<'PY'
import json, sys
raw = sys.argv[1]
GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"
def ok(m):  print(f"  {GREEN}PASS{RESET}  {m}")
def bad(m): print(f"  {RED}FAIL{RESET}  {m}"); sys.exit(1)

try:
    d = json.loads(raw)
except ValueError:
    bad(f"response was not JSON: {raw[:120]}")

for field in ("score", "label", "nearest_homolog", "top_features", "features", "explanation"):
    if field not in d:
        bad(f"missing field the UI needs: {field}")
ok("response carries every field the UI needs")

score = d["score"]
if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
    bad(f"score is not a probability: {score!r}")
ok(f"score in range: {score}")

if score < 0.5:
    print(f"  ----  synthetic control scored {score}; this is not an experimentally verified positive")
if d['label'] not in ('protective', 'other_idp'):
    bad(f"unexpected label: {d['label']!r}")
ok(f"synthetic control scored successfully ({score}), label={d['label']!r}")

if len(d["top_features"]) < 1:
    bad("no feature contributions returned — the 'why' panel will be empty")
ok(f"{len(d['top_features'])} feature contributions returned")

# Gemini vs offline: the fallback prints the raw variable name, Gemini writes prose.
expl = d["explanation"]
if not expl.strip():
    bad("explanation is empty")
if "Separate auxiliary biophysical model signals:" in expl:
    print("  ----  explanation came from the OFFLINE fallback, not Gemini")
    print("        (fine for a demo; check GEMINI_API_KEY in the server's .env to enable it)")
else:
    ok("explanation looks like Gemini prose, not the offline template")
print(f"  ----  nearest homolog: {d['nearest_homolog']}")
PY
python_status=$?
[[ $python_status -ne 0 ]] && fail=1

say
if [[ $fail -eq 0 ]]; then
  say "All checks passed — the site is demo-ready."
else
  say "Something is wrong. See the FAIL lines above."
fi
exit $fail
