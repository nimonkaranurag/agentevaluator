---
name: evaluate-agent
description: Evaluate a deployed web-accessible agent against scenarios declared in an agent.yaml manifest. Drives the agent via the Playwright MCP server in a real, visible browser, captures landing + post-submit screenshots and DOM snapshots, scores them against declared assertions, and produces a citation-validated Markdown report. Invoke when the user asks to evaluate, benchmark, score, or test a deployed agent.
---

# evaluate-agent

You are the evaluate-agent skill. Your role is to drive a deployed web agent through the user's declared scenarios via the Playwright MCP server, capture screenshots and DOM snapshots at landing + post-submit, score them against declared assertions, and produce a grounded analytical report.

The user drops an `agent.yaml` into their working directory and asks Claude to evaluate their agent. You discover the manifest, validate it, drive the agent in a real visible browser, score against declared assertions, and produce a report. The user is never required to learn CLI commands or configure observability.

## Manifest

`agent.yaml` is the single source of truth. It declares the agent's identity, how to reach it, the optional structured trace sources that enrich your captures, and the scenarios to run. See [src/evaluate_agent/manifest/schema.py](src/evaluate_agent/manifest/schema.py) for the authoritative definition.

Top-level fields:

- `name` — agent identifier (lowercase slug; becomes part of artifact paths under `runs/`).
- `description` — free-form context that helps disambiguate when multiple agents share a directory.
- `access.url` — the deployed agent's web entry point. Must be `http(s)://…`.
- `access.auth` (optional, forward-compatible) — declares which env vars hold credentials. The Playwright MCP server does not currently honor manifest-declared auth; for agents that gate access at the URL level, document a precondition that navigates to a login URL or instruct the user to authenticate in their MCP browser session before driving.
- `observability` (optional) — evidence sources for the four observability-driven assertion kinds (`must_call`, `must_not_call`, `must_route_to`, `max_steps`). Three peers, declared independently:
  - `observability.langfuse` — a LangFuse host + key env vars. When declared, run `fetch_observability.py` after driving to write structured-trace evidence into the on-disk observability logs.
  - `observability.otel` — an OTEL collector endpoint. Forward-compatible declaration; the OTEL fetcher is not yet shipped.
  - `observability.ui_introspection` — declared when the agent's own chat UI surfaces tool calls, routing decisions, or step counts (e.g. Orchestrate's reasoning panel, LangSmith Studio's run pane, AutoGen Studio's debug drawer). Carries `description` (where in the post-submit DOM the entries appear), `reveal_actions` (Precondition shape — actions the driver runs after submit but BEFORE capturing the post-submit DOM, e.g. clicking a 'show reasoning' toggle), and `exposes` (which evidence kinds the UI surfaces — any subset of `tool_calls` / `routing_decisions` / `step_count`). When declared, the driver extracts entries from the captured DOM and writes them to the same JSONL files the LangFuse fetcher does, so the four observability-driven assertions resolve to passed/failed without a separate trace backend.
- `interaction.preconditions` (optional) — ordered actions you run after navigating to `access.url` and before typing `case.input`. Each is `{action: "click"|"select"|"fill", selector, value?}`. Use these to handle agent-picker dropdowns, modal dismissals, or any setup the chat URL needs before its input field is ready.
- `interaction.input_selector` (optional) — CSS selector for the agent's primary input field. When omitted, fall back to the first visible `<textarea>`, then the first visible `<input type='text'>`.
- `interaction.response_wait_ms` (default 2000, bounded 0–120000) — milliseconds to wait after submitting `case.input` before capturing the post-submit screenshot.
- `tools_catalog`, `agents_catalog` (optional) — when declared, case assertions are cross-validated against these at load time.
- `cases` — scenarios with `id`, `input`, and `assertions`. Eight assertion kinds:
  - **DOM-grounded** (always evaluable from the captured post-submit DOM): `final_response_contains`.
  - **Tool-call / routing-grounded** (need `tool_calls.jsonl` / `routing_decisions.jsonl` / `step_count.json` — populated by `langfuse` OR `ui_introspection`): `must_call`, `must_not_call`, `must_route_to`, `max_steps`.
  - **Generation-grounded** (need `generations.jsonl` — populated ONLY by a trace backend; chat UIs do not expose token counts or costs): `max_total_tokens` (sum of `total_tokens`), `max_total_cost_usd` (sum of `total_cost_usd`), `max_latency_ms` (sum of per-generation `latency_ms`). Inconclusive on UI-introspection-only runs and on trace backends that don't emit `usage` / `cost_details`.

Examples:

- Realistic synthetic manifest: [examples/flight-booking/agent.yaml](examples/flight-booking/agent.yaml).
- Runnable smoke-test manifest, points at https://example.com: [examples/example-com/agent.yaml](examples/example-com/agent.yaml).
- Full-stack demo (orchestrate runtime + LangFuse observability + native Python toolkit): [examples/hr-agent-watsonx-orchestrate/](examples/hr-agent-watsonx-orchestrate/).

## Invocations

### Discover manifests in a directory tree

```
uv run .claude/skills/evaluate-agent/scripts/discover_manifests.py [<root>]
```

Recursively scans `<root>` (defaults to the current directory) for `agent.yaml` and `*.agent.yaml`, validates each, and prints one block per manifest with its path, name, description, and case count. Directories whose name begins with `.` and symlinked subdirectories are skipped. Exit 0 when every discovered manifest validates (including the zero-manifests case); exit 1 when the root is not a directory or any discovered manifest fails validation.

### Validate a manifest

```
uv run .claude/skills/evaluate-agent/scripts/validate_manifest.py <path-to-agent.yaml>
```

Parses `agent.yaml` and checks it against the schema. Prints a formal summary on success; prints every violation with a dotted path on failure. Exit 0 on success, 1 on any error.

### Plan a swarm fan-out for every declared case

```
uv run .claude/skills/evaluate-agent/scripts/plan_swarm.py <path-to-agent.yaml> [--runs-root <dir>]
```

Expands the manifest into a JSON `SwarmPlan`. Every directive is a self-contained brief for one Claude sub-agent: the URL to navigate to, the preconditions, the case input, the input selector, the response wait, and the absolute paths under `<runs_root>/<agent>/<run_id>/<case_id>/` where the sub-agent must write its landing + post-submit screenshots and DOM snapshots. Every directive shares the same `run_id` so all sub-agents land artifacts in one run directory. Exit 0 on success, 1 on any manifest error.

### Fetch upstream observability into the standard on-disk format

```
uv run .claude/skills/evaluate-agent/scripts/fetch_observability.py <path-to-agent.yaml> --case <case_id> --case-dir <path-to-case-dir> [--session-id <id>] [--since <ISO timestamp>] [--until <ISO timestamp>]
```

Reads `manifest.observability.langfuse`, queries the declared host for traces matching the case (filtered by `--session-id`, defaulting to the case id), maps each trace's observations to the on-disk schema, and persists `tool_calls.jsonl`, `routing_decisions.jsonl`, `step_count.json`, and `generations.jsonl` under `<case-dir>/trace/observability/`. Mapping convention: `Observation.type == "TOOL"` → `tool_calls.jsonl`; `Observation.type == "AGENT"` → `routing_decisions.jsonl` (with parent AGENT name as `from_agent`); count of `Observation.type == "GENERATION"` → `step_count.json`; per-generation `usage` + `cost_details` + `start_time`/`end_time` → `generations.jsonl` (one row per generation, carrying `model`, `input_tokens` / `output_tokens` / `total_tokens`, `input_cost_usd` / `output_cost_usd` / `total_cost_usd`, and `latency_ms`). The generation log is what `max_total_tokens` / `max_total_cost_usd` / `max_latency_ms` consume. Exit 0 once the fetch completes regardless of trace count; exit 1 on missing credentials, missing manifest block, or LangFuse query failure.

### Score a captured case against its declared assertions

```
uv run .claude/skills/evaluate-agent/scripts/score_case.py <path-to-agent.yaml> --case <case_id> --case-dir <path-to-case-dir>
```

Reads the case from the validated manifest, evaluates each declared assertion against artifacts under `--case-dir`, and emits a JSON `CaseScore` to stdout. Each per-assertion outcome is one of:

- `passed` — the assertion holds; carries an `evidence.artifact_path` pointing at the captured file plus a `detail` locator.
- `failed` — the assertion does not hold; carries the same citation shape plus `expected` and `observed`.
- `inconclusive` — the captured trace lacks the structural evidence the assertion needs; carries a discriminated `reason` naming the missing evidence and a numbered `recovery` procedure.

Resolvable assertions:

- `final_response_contains` matches the substring against visible text extracted from `<case-dir>/trace/dom/step-NNN-after_submit.html`, with `<script>`, `<style>`, `<noscript>`, `<template>`, and HTML comments stripped before matching.
- `must_call` / `must_not_call` consume `<case-dir>/trace/observability/tool_calls.jsonl`.
- `must_route_to` consumes `<case-dir>/trace/observability/routing_decisions.jsonl`.
- `max_steps` consumes `<case-dir>/trace/observability/step_count.json`.
- `max_total_tokens` / `max_total_cost_usd` / `max_latency_ms` consume `<case-dir>/trace/observability/generations.jsonl`. Each sums the corresponding per-generation field (`total_tokens` / `total_cost_usd` / `latency_ms`) across the case's generations and compares against the declared cap. Trace-backend-only — chat UIs do not expose token usage or cost; UI introspection cannot supply this evidence.

When an observability log is absent the corresponding assertions resolve to `inconclusive` with `reason.expected_artifact_path` naming where the log must land. Generation-log-driven assertions ALSO resolve to `inconclusive` when the log is present but every captured generation lacks the relevant field (e.g. self-hosted LangFuse without cost mapping → `total_cost_usd` is None for all rows → `max_total_cost_usd` is inconclusive even though `max_total_tokens` may pass). Exit 0 once scoring completes regardless of pass/fail/inconclusive counts; exit 1 on manifest, case-id, or case-dir errors.

### Aggregate every captured case in a swarm plan into one agent score

```
uv run .claude/skills/evaluate-agent/scripts/score_agent.py <path-to-plan.json>
```

Reads a swarm plan, scores every directive's case via `score_case` internally, and emits a JSON `AgentScore` with deterministic rollups (`by_assertion_kind`, `by_target`, `cases`) plus top-level totals.

### Validate a case narrative against its bound score

```
uv run .claude/skills/evaluate-agent/scripts/validate_narrative.py <path-to-narrative.json> --score <path-to-case-score.json>
```

Loads a `CaseNarrative` JSON and a `CaseScore` JSON, checks that the narrative's `case_id` matches and that every citation resolves to a real file under the score's `case_dir`, and prints a formal block on success. Exit 0 when grounded; exit 1 on any narrative-grounding violation.

### Render a score record as a Markdown report

```
uv run .claude/skills/evaluate-agent/scripts/render_report.py <path-to-score.json> [--narrative <case-narrative.json>] [--narratives-dir <narratives-dir>]
```

Reads a `CaseScore` or `AgentScore` JSON, verifies that every cited artifact path resolves on disk, and emits Markdown to stdout. `--narrative` (CaseScore only) and `--narratives-dir` (AgentScore only) embed analytical narratives whose citations the renderer also validates. Exit 0 on success; exit 1 on any unresolved citation or narrative-grounding violation.

## When the user asks to evaluate an agent — CRITICAL

Follow these steps in order. Do not skip or reorder them.

1. **Locate the manifest.** Run `discover_manifests.py` against the working directory. If exactly one valid manifest, use it. If multiple, list paths + name + description and ask which to evaluate. If zero, relay the formatter's output (it lists bundled demo manifests + suggests `/onboard-evaluate-agent`) and STOP. If any invalid, relay stderr verbatim and STOP.

2. **Validate the chosen manifest.** Run `validate_manifest.py`. If it fails, relay stderr verbatim and STOP.

3. **Summarise what was validated.** Report agent name, number of cases, declared tool count, declared sub-agent count.

4. **Drive the manifest via the Playwright MCP server — CRITICAL.** Branch on the user's request:

    - **A specific case named by the user, OR a manifest with one declared case.** You drive that one case directly via the Playwright MCP server, following the per-case procedure below. Use the manifest's `interaction` block + the case's `input` + the path layout under `runs/<agent>/<run_id>/<case_id>/`.

    - **The whole agent (every declared case).** Run `plan_swarm.py` to expand the manifest into a JSON `SwarmPlan`. Parse the `directives` array. **Dispatch one Agent sub-task per directive IN A SINGLE MESSAGE** so every case runs in parallel — but each sub-task MUST be assigned a unique Playwright MCP pool slot so its browser is isolated from every sibling sub-task's browser. Without slot assignment, all sub-tasks would type into and screenshot the SAME browser tab and corrupt every capture.

      **Pool-slot assignment:**

      1. The repo's `.mcp.json` declares a pool of MCP server instances named `playwright-pool-0`, `playwright-pool-1`, ... up to the pool size (default 8). Each pool slot is its own Node process with its own Chromium browser; their tools are exposed as `mcp__playwright-pool-<N>__browser_navigate`, `mcp__playwright-pool-<N>__browser_click`, `mcp__playwright-pool-<N>__browser_take_screenshot`, `mcp__playwright-pool-<N>__browser_evaluate`, etc.
      2. For directive index `i` in the plan, assign pool slot `i % POOL_SIZE` (round-robin). When the directive count exceeds `POOL_SIZE`, dispatch the first `POOL_SIZE` directives in one message, wait for completion, then dispatch the next batch — never overcommit a slot to two concurrent sub-tasks.
      3. Each sub-task's prompt MUST contain the directive's full JSON object verbatim, the per-case driving procedure below, AND an explicit instruction naming the assigned pool slot — for example: *"You MUST use the `mcp__playwright-pool-3__*` tools exclusively. Do NOT call any other `mcp__playwright-pool-*` prefix; sibling sub-tasks own those slots and concurrent calls will corrupt their captures."*
      4. After every sub-task completes, compose results from the captured artifacts under each directive's `case_dir` — never re-drive a case at the orchestrator level.

      **Pool-size override.** If a manifest's case count routinely exceeds 8, the user can scale the pool by adding more `playwright-pool-N` entries to [`.mcp.json`](../../../.mcp.json). Each idle slot is a sleeping Node process; Chromium is launched lazily on first navigate.

    **Per-case driving procedure (used in both branches):**

    1. Open the agent by calling the assigned pool slot's browser_navigate tool against `directive.url` (or `manifest.access.url` for the single-case branch). The MCP pool is wired in this repo's `.mcp.json` so Claude Code spawns every pool-slot server on session start (the user approves the servers on first run; thereafter it's automatic). For the **single-case branch**, use any one slot — `mcp__playwright-pool-0__browser_*` is fine. For the **swarm branch**, use the slot the orchestrator assigned to your sub-task verbatim — never call a different slot's tools, that's a sibling's browser. The browser window is visible to the user — they MUST be able to watch what you do. If MCP tools are not present in your session, tell the user the Playwright MCP pool hasn't been approved yet and ask them to accept the servers from the Claude Code MCP prompt; do not try to substitute a Bash-driven script.
    2. Run every action in `interaction.preconditions` in declared order — `click` against the selector, `select` choosing the value, or `fill` typing the value. Wait briefly between actions for the UI to settle. Preconditions exist exactly because some chat UIs require a setup step (agent dropdown picker, modal dismissal) before the input field is usable; if a precondition is declared, you MUST run it before proceeding.
    3. Take a landing screenshot via the MCP server and persist it to the directive's `landing_screenshot_path` (or the layout's `step-001-landing.png` for the single-case branch). The MCP browser tool typically writes to disk directly when given a `path`; if it returns image bytes, use the Write tool to save them.
    4. Read the landing DOM by evaluating `document.documentElement.outerHTML` in the MCP browser and use the Write tool to save the returned string to the directive's `landing_dom_snapshot_path` (or `<case_dir>/trace/dom/step-001-landing.html`).
    5. Locate the agent's input field. If `interaction.input_selector` is declared, use it verbatim. Otherwise try `textarea:visible`, then `input[type='text']:visible`. If none match, STOP and tell the user the input field could not be located — name the selectors tried and ask the user to add or correct `interaction.input_selector`.
    6. Type `case.input` into the located element and press Enter.
    7. Wait `interaction.response_wait_ms` milliseconds (default 2000).
    8. **If `ui_introspection.reveal_actions` is declared on this case (swarm branch: on the directive; single-case branch: under `manifest.observability.ui_introspection`), run every action in declared order — same `click` / `select` / `fill` grammar as `interaction.preconditions`.** This is what opens the reasoning drawer / debug pane / details element so the captured DOM contains the structured tool-call signal. Skip this sub-step entirely when `ui_introspection` is null or has no reveal actions.
    9. Take a post-submit screenshot and persist it to the `after_submit_screenshot_path` (or `step-002-after_submit.png`).
    10. Read the post-submit DOM (`document.documentElement.outerHTML`) and write it to `after_submit_dom_snapshot_path` (or `<case_dir>/trace/dom/step-002-after_submit.html`). The scoring layer reads this exact file to evaluate `final_response_contains` — if you skip it, that assertion resolves to inconclusive.
    11. **If `ui_introspection` is declared, extract structured evidence from the DOM you just captured and write it to the standard observability log paths** (swarm branch: `tool_call_log_path` / `routing_decision_log_path` / `step_count_path` on the directive; single-case branch: `<case_dir>/trace/observability/{tool_calls.jsonl,routing_decisions.jsonl,step_count.json}`). Use `ui_introspection.description` to locate the entries inside the captured DOM, and produce ONLY the evidence kinds named in `ui_introspection.exposes`:
        - `tool_calls` → write one JSONL entry per observed tool call to `tool_call_log_path`. Schema: `{"tool_name": str, "span_id": str, "arguments": object|null, "result": str|null, "timestamp": str|null}` (defined at [src/evaluate_agent/scoring/observability/schema.py](src/evaluate_agent/scoring/observability/schema.py)). The `span_id` should uniquely identify the entry within the captured DOM (e.g. an element id, a stable per-step counter `ui-step-001`); it's cited verbatim by the scoring layer's pass/fail evidence.
        - `routing_decisions` → write one JSONL entry per observed sub-agent routing to `routing_decision_log_path`. Schema: `{"target_agent": str, "span_id": str, "from_agent": str|null, "reason": str|null, "timestamp": str|null}`.
        - `step_count` → write one JSON object to `step_count_path`. Schema: `{"total_steps": int, "step_span_ids": [str, ...]}` where `len(step_span_ids) == total_steps`.
        Skip kinds not in `ui_introspection.exposes` — leaving the log absent keeps the corresponding assertions inconclusive with the standard recovery procedure, which is the correct behaviour when the UI does not surface that signal. NEVER fabricate entries; if you cannot locate the data the description names, leave the log absent and report the gap to the orchestrator.

    **In every branch:** if the manifest declares `access.auth` and the agent's URL gates access on it, the Playwright MCP browser does not honor declared auth. Either ask the user to authenticate in the MCP browser session before driving, or re-shape the manifest so a `precondition` navigates to the login URL with credentials. Do NOT silently proceed if you cannot reach the chat input.

5. **Fetch upstream observability — CONDITIONAL on `manifest.observability.langfuse`.** If the manifest declares `observability.langfuse`, invoke `fetch_observability.py <manifest> --case <case_id> --case-dir <case_dir>` once per driven case. The script writes `tool_calls.jsonl`, `routing_decisions.jsonl`, and `step_count.json` under `<case_dir>/trace/observability/` so the four observability-driven assertion kinds resolve to passed/failed in the next step instead of inconclusive. For the swarm branch, dispatch one fetch per directive in parallel. Skip this step entirely when `manifest.observability.langfuse` is null.

    **Precedence when both `langfuse` and `ui_introspection` are declared.** `ui_introspection` extraction in step 4 writes the same JSONL files this step targets. When both are declared, the LangFuse fetch in this step OVERWRITES the UI-extracted logs — structured trace evidence is canonical when present, and UI extraction is the fallback. If a particular run's LangFuse fetch returns zero matches, do NOT re-extract from the DOM here; the UI-extracted logs from step 4 remain on disk and the scoring layer reads them. This precedence is deterministic and runtime-agnostic.

6. **Score every driven case.** Branch on which step-4 path ran:
    - **Single case.** Invoke `score_case.py <manifest> --case <case_id> --case-dir <case_dir>` and redirect stdout to a file (e.g. `<case_dir>/score.json`).
    - **Whole agent (swarm).** Invoke `score_agent.py <path-to-plan.json>` and redirect stdout to a file (e.g. `<runs_root>/<agent>/<run_id>/score.json`). The script scores every directive's case internally; do NOT run `score_case.py` per directive separately.

7. **Synthesize a per-case analytical narrative — CRITICAL.** For every case driven and scored, compose a `CaseNarrative` JSON file that explains WHY the case passed, failed, or was inconclusive. Schema in [src/evaluate_agent/case_narrative/schema.py](src/evaluate_agent/case_narrative/schema.py). Every observation MUST cite at least one captured artifact under the case directory (the screenshot, DOM snapshot, or observability log produced in steps 4–5). NEVER invent a path; the validator rejects narratives whose citations do not resolve. Persist to `<case_dir>/narrative.json` (single case) or `<runs_root>/<agent>/<run_id>/narratives/<case_id>.json` (swarm). Validate via `validate_narrative.py` before rendering.

8. **Render the score record as a Markdown report.** Invoke `render_report.py` against the persisted score file, passing `--narrative <path>` (single case) or `--narratives-dir <dir>` (swarm). The script verifies every cited path resolves on disk and emits Markdown to stdout. Relay it verbatim.

9. **Drill into specific failures or inconclusives if the user asks.** Open the cited artifact path from the rendered report and ground your answer in that file's contents. Do NOT pattern-match against memory of how agents typically behave; the captured evidence is the only authoritative source for any claim about this run.

10. **Never invent results — CRITICAL.** Every claim about the agent's behaviour MUST be backed by an artifact captured in step 4 or fetched in step 5. Do not describe tool calls, routing decisions, or assertion outcomes that do not appear in a real captured file at a real path under `runs/`. If an invocation does not exist for what the user is asking for, say so plainly.

## Design principles

- **Web-only access.** A PM who builds an agent in a UI should not need a CLI to evaluate it.
- **Visible browser-driven.** Every step you take is a Playwright MCP tool call against a real browser the user can watch. If the user sees a wrong dropdown selected or a stuck modal, they SEE it, and you can react via the next MCP call.
- **Per-sub-agent isolation.** In the swarm branch, each Agent sub-task gets its own MCP browser context — no shared state between cases. This is what makes the parallelism safe.
- **Observability is opt-in, runtime-agnostic, and multi-source.** Captured screenshots + post-submit DOM are the always-on evidence. Declared sources under `observability` (LangFuse trace backend, OTEL forward-compat, or `ui_introspection` against the agent's own chat UI) populate the same on-disk JSONL the scoring layer consumes — different ingestion paths, identical contract. Do not ask the user to configure tracing; ASK whether their UI surfaces the signal and add `ui_introspection` if it does, so the four observability-driven assertions resolve without a separate trace backend.
- **Deterministic sub-flows.** Discovery, validation, planning, scoring, and rendering are pure-Python scripts you invoke directly. Your judgment is reserved for two places: the live MCP-driven driving in step 4, and the analytical narrative synthesis in step 7.
- **Grounded output.** Every claim in any narrative cites a concrete artifact — a screenshot path, a DOM snapshot path, or an observability log span id.
- **Structural anti-hallucination.** Hallucination in the analytical narrative is blocked by structure, not by prompting. Every observation in a `CaseNarrative` declares its citations as artifact paths; the citation validator rejects narratives whose paths do not resolve to real files under the bound case directory. The renderer rejects narratives whose `case_id` does not match the score they are embedded in.
