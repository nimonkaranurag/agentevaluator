#!/usr/bin/env bash
###############################################################################
# import_all.sh — Import the People Directory demo agent into watsonx
# Orchestrate so the agentevaluator manifest in the parent directory has
# something to drive end to end.
#
# Usage:
#   ./_resources/import_all.sh
#
# What it does:
#   1. Sanity-checks the orchestrate CLI is on PATH and the dev server is up.
#   2. Imports the native-Python tools file (3 tools).
#   3. Imports the agent definition.
#   4. Lists the imported tools and the agent so the operator sees the result.
#
# Re-runnable: every step prints whether it created or updated, and a
# pre-existing tool / agent is treated as success rather than failure.
###############################################################################

set -uo pipefail

# ---------------------------------------------------------------------------
# Cosmetics
# ---------------------------------------------------------------------------

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 \
    && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  C_RESET="$(tput sgr0)"
  C_BOLD="$(tput bold)"
  C_DIM="$(tput dim)"
  C_RED="$(tput setaf 1)"
  C_GREEN="$(tput setaf 2)"
  C_YELLOW="$(tput setaf 3)"
  C_BLUE="$(tput setaf 4)"
  C_CYAN="$(tput setaf 6)"
else
  C_RESET=""; C_BOLD=""; C_DIM=""
  C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_CYAN=""
fi

step()    { printf '%s[%s]%s %s\n' "$C_BOLD$C_BLUE" "$1" "$C_RESET" "$2"; }
ok()      { printf '  %s%s%s %s\n' "$C_GREEN" "✓" "$C_RESET" "$1"; }
warn()    { printf '  %s%s%s %s\n' "$C_YELLOW" "!" "$C_RESET" "$1"; }
info()    { printf '  %s%s%s\n'    "$C_DIM"   "$1" "$C_RESET"; }
fail() {
  printf '\n%s%s ERROR%s — %s\n' \
    "$C_BOLD$C_RED" "✗" "$C_RESET" "$1" >&2
  if [[ $# -gt 1 ]]; then
    printf '\n%sTo resolve:%s\n' "$C_BOLD" "$C_RESET" >&2
    shift
    printf '  %s\n' "$@" >&2
  fi
  exit 1
}
copy() {
  printf '    %s$%s %s%s%s\n' \
    "$C_DIM" "$C_RESET" "$C_CYAN" "$1" "$C_RESET" >&2
}

# ---------------------------------------------------------------------------
# Locate resources
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_FILE="$SCRIPT_DIR/tools/people_directory_tools.py"
AGENT_FILE="$SCRIPT_DIR/agents/people_directory_agent.yaml"
LOCAL_LANGFUSE_URL="http://localhost:3010"
AGENT_NAME="people_directory_agent"

printf '%s%s== People Directory demo — Orchestrate import ==%s\n\n' \
  "$C_BOLD" "$C_CYAN" "$C_RESET"
info  "example dir: $EXAMPLE_DIR"
info  "tools file:  $TOOLS_FILE"
info  "agent file:  $AGENT_FILE"
echo

# ---------------------------------------------------------------------------
# 1. Preflight — orchestrate CLI present
# ---------------------------------------------------------------------------

step "1/4" "Checking the orchestrate CLI is on PATH"
if ! command -v orchestrate >/dev/null 2>&1; then
  printf '\n%s%s ERROR%s — the %sorchestrate%s CLI is not on PATH.\n' \
    "$C_BOLD$C_RED" "✗" "$C_RESET" "$C_BOLD" "$C_RESET" >&2
  printf '\n%sTo install the watsonx Orchestrate ADK:%s\n\n' \
    "$C_BOLD" "$C_RESET" >&2
  copy "pip install --upgrade ibm-watsonx-orchestrate"
  printf '\n%sthen verify with:%s\n\n' "$C_BOLD" "$C_RESET" >&2
  copy "orchestrate --version"
  printf '\n%sIf you use a different package manager:%s\n\n' \
    "$C_BOLD" "$C_RESET" >&2
  copy "uv pip install ibm-watsonx-orchestrate"
  copy "pipx install ibm-watsonx-orchestrate"
  printf '\nDocs: %shttps://developer.watson-orchestrate.ibm.com/%s\n' \
    "$C_CYAN" "$C_RESET" >&2
  exit 1
fi
ok "orchestrate found at $(command -v orchestrate)"

# ---------------------------------------------------------------------------
# 2. Preflight — orchestrate server running and an env active
# ---------------------------------------------------------------------------

step "2/4" "Checking the orchestrate dev server is reachable"
if ! orchestrate env list >/dev/null 2>&1; then
  printf '\n%s%s ERROR%s — %sorchestrate env list%s failed.\n' \
    "$C_BOLD$C_RED" "✗" "$C_RESET" "$C_BOLD" "$C_RESET" >&2
  printf '\nThe most common cause is that the dev server is not running.\n' >&2
  printf '\n%sTo start it:%s\n\n' "$C_BOLD" "$C_RESET" >&2
  copy "orchestrate server start"
  printf '\n%sthen activate the local env:%s\n\n' "$C_BOLD" "$C_RESET" >&2
  copy "orchestrate env activate local"
  printf '\n%sthen re-run:%s\n\n' "$C_BOLD" "$C_RESET" >&2
  copy "$0"
  exit 1
fi

ACTIVE_ENV="$(orchestrate env list 2>/dev/null \
  | awk '/\(active\)/ {print $1; exit}')"
if [[ -z "${ACTIVE_ENV}" ]]; then
  printf '\n%s%s ERROR%s — no orchestrate environment is currently active.\n' \
    "$C_BOLD$C_RED" "✗" "$C_RESET" >&2
  printf '\n%sList environments:%s\n\n' "$C_BOLD" "$C_RESET" >&2
  copy "orchestrate env list"
  printf '\n%sActivate one (typically %slocal%s for the dev server):%s\n\n' \
    "$C_BOLD" "$C_BOLD" "$C_RESET$C_BOLD" "$C_RESET" >&2
  copy "orchestrate env activate local"
  exit 1
fi
ok "active env: $ACTIVE_ENV"

# ---------------------------------------------------------------------------
# 3. Verify resource files
# ---------------------------------------------------------------------------

step "3/4" "Verifying resource files"
[[ -f "$TOOLS_FILE" ]] || fail \
  "tools file not found: $TOOLS_FILE" \
  "Confirm the _resources/ tree was not partially deleted; re-clone if so."
[[ -f "$AGENT_FILE" ]] || fail \
  "agent file not found: $AGENT_FILE" \
  "Confirm the _resources/ tree was not partially deleted; re-clone if so."
ok "tools file present"
ok "agent file present"

if curl -sfI --max-time 3 "$LOCAL_LANGFUSE_URL" >/dev/null 2>&1; then
  ok "local Langfuse reachable at $LOCAL_LANGFUSE_URL"
else
  warn "local Langfuse not reachable at $LOCAL_LANGFUSE_URL"
  info "Orchestrate's built-in Langfuse is opt-in. Restart the dev"
  info "server with the --with-langfuse flag so the four"
  info "observability-driven assertions resolve to passed/failed:"
  copy "orchestrate server stop && orchestrate server start --with-langfuse"
  info "Then sign in (orchestrate@ibm.com / orchestrate), generate"
  info "an API key pair from Settings -> API Keys, and export them:"
  copy "export LANGFUSE_PUBLIC_KEY=pk-lf-..."
  copy "export LANGFUSE_SECRET_KEY=sk-lf-..."
fi

# ---------------------------------------------------------------------------
# 4. Import tools then agent
# ---------------------------------------------------------------------------

step "4/4" "Importing tools and agent"

run_orchestrate() {
  local label="$1"; shift
  local out
  out="$("$@" 2>&1)"
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    ok "$label: imported"
    return 0
  fi
  if grep -qiE 'already exists|conflict|duplicate' <<<"$out"; then
    warn "$label: already present — left as-is"
    return 0
  fi
  printf '\n%s%s ERROR%s — orchestrate %s failed (exit %s).\n' \
    "$C_BOLD$C_RED" "✗" "$C_RESET" "$label" "$rc" >&2
  printf '\n%sCommand stdout/stderr:%s\n%s\n\n' \
    "$C_BOLD" "$C_RESET" "$out" >&2
  printf '%sCommon causes:%s\n' "$C_BOLD" "$C_RESET" >&2
  printf '  - The dev server crashed; restart with:\n' >&2
  copy "orchestrate server restart"
  printf '  - The toolkit/agent name conflicts with an unrelated import.\n' >&2
  printf '    List, then remove or rename the conflicting record:\n' >&2
  copy "orchestrate tools list"
  copy "orchestrate agents list"
  copy "orchestrate tools delete --name <name>"
  copy "orchestrate agents delete --name <name>"
  exit 1
}

run_orchestrate "python tools file" \
  orchestrate tools import -k python -f "$TOOLS_FILE"
run_orchestrate "agent definition" \
  orchestrate agents import -f "$AGENT_FILE"

# ---------------------------------------------------------------------------
# Closing — point at the next step
#
# Both import sub-commands above already returned 0 (or were short-circuited
# as "already present"), so the imports succeeded as far as the dev server
# is concerned. A post-hoc `orchestrate tools list` / `agents list` cross-
# check was deliberately removed: those commands hit auxiliary services
# (e.g. the connections registry on port 3001) that may not be running
# alongside the dev server, and the agents-list table wraps long names
# across cells in a way that defeats `grep`. The exit codes of the import
# commands above are the load-bearing signal.
# ---------------------------------------------------------------------------

echo
printf '%s%sImport complete.%s\n\n' "$C_BOLD" "$C_GREEN" "$C_RESET"
printf '%sNext steps:%s\n' "$C_BOLD" "$C_RESET"
printf '  1. Open the chat UI:\n'
copy "orchestrate chat start"
printf '  2. From Claude Code in the repo root, run:\n'
copy "/evaluate-agent"
printf '  3. Claude discovers the manifest, drives every case in a\n'
printf '     visible Playwright MCP browser (the dropdown precondition\n'
printf '     in the manifest selects %s%s%s for you), pulls\n' \
  "$C_BOLD" "$AGENT_NAME" "$C_RESET"
printf '     LangFuse traces, scores, narrates, and renders.\n'
echo
