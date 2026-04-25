---
name: evaluate-agent
description: Evaluate a deployed web-accessible agent against scenarios declared in an agent.yaml manifest. Drives the agent through its user-facing web interface in a sandboxed Playwright browser, captures the full interaction trace, scores the trace against declared assertions, and produces a grounded analysis report. Invoke when the user asks to evaluate, benchmark, score, or test a deployed agent.
---

# evaluate-agent

You are the evaluate-agent skill. Your role is to help the user evaluate a deployed web agent by driving it through the user's declared scenarios in a sandboxed Playwright browser, capturing the full interaction trace, scoring the trace against declared assertions, and producing a grounded analysis report.

The user drops an `agent.yaml` into their working directory and asks Claude to evaluate their agent. You discover the manifest, validate it, drive the agent, capture artifacts, score against declared assertions, and produce a report. The user is never required to learn CLI commands or configure observability.

## Manifest

`agent.yaml` is the single source of truth for every part of evaluation. It declares the agent's identity, how to reach it, the optional trace sources that enrich Playwright's baseline capture, and the scenarios to run. See [src/evaluate_agent/manifest/schema.py](src/evaluate_agent/manifest/schema.py) for the authoritative definition.

Top-level fields:

- `name` — agent identifier (lowercase slug; becomes part of artifact paths under `runs/`).
- `description` — free-form context that helps disambiguate when multiple agents share a directory.
- `access.url` — the deployed agent's web entry point. Must be `http(s)://…`.
- `access.auth` (optional) — declares which env vars hold credentials (`type: bearer` with `token_env`, or `type: basic` with `username_env` and `password_env`). NEVER embed literal secrets in the manifest.
- `observability` (optional) — additional structured trace sources (Langfuse, OTEL). Playwright capture is the always-on baseline regardless of this section.
- `interaction` (optional) — driver hints for the agent's web UI. `input_selector` is an optional CSS selector for the primary input field (when omitted, the driver falls back to the first visible `<textarea>`, then the first visible `<input type='text'>`). `response_wait_ms` (default 2000, bounded 0–120000) is the wait after submitting `case.input` before the post-submit screenshot.
- `tools_catalog`, `agents_catalog` (optional) — when declared, case assertions are cross-validated against these at load time. An empty or omitted catalog disables the cross-check.
- `cases` — scenarios with `id`, `input`, and `assertions` (`must_call`, `must_not_call`, `must_route_to`, `max_steps`, `final_response_contains`).

Examples:

- Realistic synthetic manifest: [examples/flight-booking/agent.yaml](examples/flight-booking/agent.yaml).
- Runnable smoke-test manifest, points at https://example.com: [examples/example-com/agent.yaml](examples/example-com/agent.yaml).

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

### Open the agent and capture artifacts for one case

```
uv run playwright install chromium                              # one-time, per machine
uv run .claude/skills/evaluate-agent/scripts/open_agent.py <path-to-agent.yaml> --case <case_id> [--submit] [--runs-root <dir>] [--run-id <YYYYMMDDTHHMMSSZ>] [--headed]
```

Opens the declared URL in a sandboxed Chromium browser, resolves `access.auth` from the env vars named in the manifest (bearer or basic), navigates to the page, and captures `runs/<agent_name>/<run_id>/<case_id>/step-001-landing.png` paired with a full-DOM snapshot at `<case_dir>/trace/dom/step-001-landing.html`. With `--submit`: locates the primary input field (manifest-declared `interaction.input_selector` wins; otherwise heuristic fallback over `textarea:visible` then `input[type='text']:visible`), types `case.input`, presses Enter, waits `interaction.response_wait_ms`, and captures `step-002-after_submit.png` paired with `<case_dir>/trace/dom/step-002-after_submit.html`. `--case` must match one of the declared `cases[].id` values. `--run-id` reuses a pre-committed UTC timestamp (format `YYYYMMDDTHHMMSSZ`) so multiple invocations write into the same `runs/<agent>/<run_id>/` directory; when omitted, a fresh timestamp is captured at invocation time. Exit 0 on success, 1 on any manifest, auth, interaction, or driver error.

Every invocation also writes baseline trace artifacts alongside the screenshots under `<case_dir>/trace/`:

- `network.har` — HTTP archive of the full browser session (request/response bodies embedded).
- `requests.jsonl` — streaming record of every outbound `request` event (method, URL, resource type, headers, UTC timestamp).
- `responses.jsonl` — streaming record of every inbound `response` event (URL, status, status text, headers, UTC timestamp).
- `console.jsonl` — streaming record of every page `console` message (type, text, source location, UTC timestamp).
- `page_errors.jsonl` — streaming record of every uncaught `pageerror` (message, UTC timestamp).
- `dom/step-<NNN>-<label>.html` — serialized rendered DOM (UTF-8 HTML) captured at each labeled screenshot point. Step number and label mirror the paired `.png` so a reader can cross-reference visual evidence with the programmatically inspectable DOM.
- `dom/auto-<NNN>-nav.html` — serialized rendered DOM captured automatically on every main-frame navigation (`framenavigated` event). Covers redirects, server-side page transitions, and client-side SPA route changes that the labeled `step-*.html` captures would miss. The `auto-` and `step-` prefixes share the same `dom/` directory without colliding; the step counters are independent.

The invocation's formal output block lists the absolute path to each trace artifact so downstream invocations can cite them directly, including one row per automatic DOM snapshot recorded under `dom/auto-*.html`.

### Plan a swarm fan-out for every declared case

```
uv run .claude/skills/evaluate-agent/scripts/plan_swarm.py <path-to-agent.yaml> [--runs-root <dir>]
```

Expands the validated manifest into a deterministic JSON fan-out plan emitted to stdout. The plan carries one shared `run_id` and one entry per case; each entry contains the absolute `case_dir` and a complete `driver_invocation` (absolute script path plus argv) sufficient to drive that case in isolation. Every entry pins the same `--run-id`, so all sibling sub-agents write artifacts into the same `runs/<agent_name>/<run_id>/` directory. Entries appear in the order the cases were declared in the manifest. Exit 0 on success, 1 on any manifest load or validation error.

### Score a captured case against its declared assertions

```
uv run .claude/skills/evaluate-agent/scripts/score_case.py <path-to-agent.yaml> --case <case_id> --case-dir <path-to-case-dir>
```

Reads the case from the validated manifest, evaluates each declared assertion against artifacts under `--case-dir`, and emits a JSON `CaseScore` record to stdout. Each per-assertion outcome is one of:

- `passed` — the assertion holds against the captured trace. Carries a citation (`evidence.artifact_path` plus a `detail` locator) that resolves to a real captured file.
- `failed` — the assertion does not hold against the captured trace. Carries the same citation shape plus the `expected` and `observed` values for the discrepancy.
- `inconclusive` — the captured trace lacks the structural evidence required to evaluate the assertion. Carries a discriminated `reason` naming the missing evidence (`dom_snapshot_unavailable` when the post-submit DOM is absent; `observability_source_missing` when the manifest does not declare the trace source the assertion needs) plus a numbered `recovery` procedure the caller follows to make the assertion evaluable on a subsequent run.

Resolvable assertion: `final_response_contains` matches the expected substring against visible text extracted from the post-submit DOM snapshot (`<case-dir>/trace/dom/step-<NNN>-after_submit.html`), with `<script>`, `<style>`, `<noscript>`, `<template>`, and HTML comments stripped before matching. Assertions sourced from observability streams (`must_call`, `must_not_call`, `must_route_to`, `max_steps`) resolve to `inconclusive` whose `reason.needed_evidence` names the trace source the manifest must declare.

Exit 0 once scoring completes, regardless of pass / fail / inconclusive counts. Exit 1 only on manifest load errors, an unknown `--case` id, or a missing / non-directory `--case-dir`.

### Aggregate every captured case in a swarm plan into one agent score

```
uv run .claude/skills/evaluate-agent/scripts/score_agent.py <path-to-plan.json>
```

Reads a swarm plan produced by `plan_swarm.py`, loads the manifest the plan references, scores every entry's case via `score_case`, and emits a JSON `AgentScore` record to stdout. The record carries every per-case `CaseScore` plus a deterministic `rollup` that aggregates outcomes along three dimensions:

- `rollup.by_assertion_kind` — one row per assertion kind that had at least one outcome, listed in the schema order `final_response_contains`, `must_call`, `must_not_call`, `must_route_to`, `max_steps`. Each row has `total / passed / failed / inconclusive` counts across every case.
- `rollup.by_target` — one row per `(assertion_kind, target)` pair for the per-target kinds (`must_call`, `must_not_call`, `must_route_to`). Sorted by assertion kind in schema order, then by target lexicographically. Each row has the same four counts; targets that appear in multiple cases sum across them.
- `rollup.cases` — case-granularity counts: `total`, `fully_passed` (cases whose every assertion outcome was `passed`), `with_any_failure` (cases with at least one failed outcome), `with_any_inconclusive` (cases with at least one inconclusive outcome — overlaps with `with_any_failure` when a case has both), `with_no_assertions` (cases that declared zero assertions and therefore have zero outcomes — mutually exclusive with `fully_passed`).

`rollup` also carries top-level `total_assertions / passed / failed / inconclusive` counts that partition every outcome across every case. The composition is deterministic: the same set of `CaseScore` records always produces the same `AgentScore` byte-for-byte.

Exit 0 once aggregation completes, regardless of pass / fail / inconclusive counts. Exit 1 on a missing or malformed plan file, a manifest load error, a plan that references case ids the manifest does not declare, or any case directory in the plan that does not exist on disk.

## When the user asks to evaluate an agent — CRITICAL

Follow these steps in order. Do not skip or reorder them.

1. **Locate the manifest.** Run `discover_manifests.py` against the working directory. If it reports exactly one valid manifest, use that path. If it reports multiple, list the paths with their `name` and `description` and ask the user which one to evaluate — do not guess. If it reports zero manifests, relay the formatter's output to the user and STOP. If it reports any invalid manifest, relay the formatter's stderr verbatim and STOP.

2. **Validate the chosen manifest.** Run `validate_manifest.py` against the chosen path to confirm it parses cleanly in isolation. If validation fails, relay the validator's stderr to the user verbatim and STOP. A partially valid manifest is never passed downstream.

3. **Summarise what was validated.** Report back to the user: agent name, number of cases, declared tool count, declared sub-agent count. This confirms which agent you loaded.

4. **Drive the manifest.** Branch on the user's request:
    - **A specific case named by the user, OR a manifest with one declared case.** Invoke `open_agent.py` directly with `--submit` and that case id. Without `--submit`, the invocation captures the landing view only — use this only when the user asks for a screenshot, to "see" the agent, or to verify access works. If the user did not specify a case id and the manifest declares more than one, list the declared ids and ask before proceeding.
    - **The whole agent (every declared case).** Invoke `plan_swarm.py` to expand the manifest into a JSON fan-out plan. Parse the plan's `entries` array. Dispatch one Agent sub-task per entry IN A SINGLE MESSAGE so every case runs in parallel under its own isolated browser context. Each sub-task's prompt must instruct the sub-agent to invoke the entry's `driver_invocation.script` with the entry's `driver_invocation.arguments` exactly as supplied — do NOT modify the argv. Every entry's argv pins the same `--run-id`, so all sibling sub-agents write into one shared `runs/<agent>/<run_id>/` directory. After all sub-tasks complete, compose results from the captured artifacts under each entry's `case_dir`; never re-run a case at the orchestrator level.
    - **In every branch:** if the manifest declares `access.auth` and the required env vars are not set, relay the `MissingAuthEnvVar` message verbatim — do not proceed without credentials. If `InputElementNotFound` is raised, relay it verbatim — the user must either set `interaction.input_selector` or correct it to match a visible element.

5. **Score every driven case.** Branch on which driver invocation step 4 ran:
    - **Single case (`open_agent.py` direct).** Invoke `score_case.py <manifest> --case <case_id> --case-dir <case_dir>` and parse the JSON `CaseScore` record. Skip step 6 — there is no swarm plan to aggregate.
    - **Whole agent (`plan_swarm.py` + sub-agent fan-out).** Invoke `score_agent.py <path-to-plan.json>` and parse the JSON `AgentScore` record. The script scores every case in the plan internally; do NOT run `score_case.py` per entry separately.

6. **Narrate results from the score records, NEVER from intuition or visual scan of the screenshots.** For each per-assertion outcome inside a `CaseScore` (or every `case_score.outcomes` inside an `AgentScore`):
    - `passed` — narrate the success and cite `evidence.artifact_path`. The path resolves to a real captured file the user can open.
    - `failed` — narrate the discrepancy with `expected` vs `observed` and cite `evidence.artifact_path`.
    - `inconclusive` — relay `reason.recovery` verbatim. Do NOT guess, infer, or pattern-match the assertion against screenshots; the inconclusive outcome means the structural evidence required for evaluation is absent. Suggest the manifest changes named in the recovery procedure (declare the named observability source, re-run with `--submit`, etc.).

   When an `AgentScore` is available, lead the narrative with the cross-case rollup before per-case detail: the `rollup.total_assertions / passed / failed / inconclusive` counts orient the user; `rollup.by_assertion_kind` shows where the agent is strong vs weak per assertion kind; `rollup.by_target` shows which tools or sub-agents were exercised and how they fared; `rollup.cases` shows how many cases passed cleanly vs need attention. Cite specific cases by `case_id` and `case_dir` when drilling into failures or inconclusives.

7. **Never invent results — CRITICAL.** Every claim you make about the agent's behaviour MUST be backed by an artifact produced by an invocation above. Do not describe tool calls, routing decisions, assertion outcomes, metrics, or summaries unless they appear in a real captured artifact at a real path under `runs/` or in a `CaseScore` / `AgentScore` record returned by the scoring scripts. If an invocation does not exist for what the user is asking for, say so plainly and offer the invocations that do exist.

## Design principles

- **Web-only access.** A PM who builds an agent in a UI should not need a CLI to evaluate it.
- **Observability is opt-in.** Playwright capture (network HAR, page event streams, screenshots) is the always-on baseline; declared sources under `observability` only enrich it. Do not ask the user to configure tracing.
- **Deterministic sub-flows.** Every sub-flow that can be scripted is a Python script invoked directly. Your role is only the parts that genuinely need judgment (analytical synthesis in the report).
- **Grounded output.** When producing narrative, every claim cites a concrete artifact — a screenshot path, a trace span id, or a manifest field.
