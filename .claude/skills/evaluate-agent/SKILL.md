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
uv run .claude/skills/evaluate-agent/scripts/open_agent.py <path-to-agent.yaml> --case <case_id> [--submit] [--runs-root <dir>] [--headed]
```

Opens the declared URL in a sandboxed Chromium browser, resolves `access.auth` from the env vars named in the manifest (bearer or basic), navigates to the page, and captures `runs/<agent_name>/<utc_timestamp>/<case_id>/step-001-landing.png`. With `--submit`: locates the primary input field (manifest-declared `interaction.input_selector` wins; otherwise heuristic fallback over `textarea:visible` then `input[type='text']:visible`), types `case.input`, presses Enter, waits `interaction.response_wait_ms`, and captures `step-002-after_submit.png`. `--case` must match one of the declared `cases[].id` values. Exit 0 on success, 1 on any manifest, auth, interaction, or driver error.

## When the user asks to evaluate an agent — CRITICAL

Follow these steps in order. Do not skip or reorder them.

1. **Locate the manifest.** Run `discover_manifests.py` against the working directory. If it reports exactly one valid manifest, use that path. If it reports multiple, list the paths with their `name` and `description` and ask the user which one to evaluate — do not guess. If it reports zero manifests, relay the formatter's output to the user and STOP. If it reports any invalid manifest, relay the formatter's stderr verbatim and STOP.

2. **Validate the chosen manifest.** Run `validate_manifest.py` against the chosen path to confirm it parses cleanly in isolation. If validation fails, relay the validator's stderr to the user verbatim and STOP. A partially valid manifest is never passed downstream.

3. **Summarise what was validated.** Report back to the user: agent name, number of cases, declared tool count, declared sub-agent count. This confirms which agent you loaded.

4. **Open and drive the case.** Invoke `open_agent.py` with the case id. Without `--submit`, the invocation captures the landing view only — use this when the user asks for a screenshot, to "see" the agent, or to verify access works. With `--submit`, the invocation additionally types `case.input` into the agent's primary input field and captures the post-submit screenshot. If the user did not specify a case id, list the declared ids and ask. If the manifest declares `access.auth` and the required env vars are not set, relay the `MissingAuthEnvVar` message verbatim — do not proceed without credentials. If `InputElementNotFound` is raised, relay it verbatim — the user must either set `interaction.input_selector` or correct it to match a visible element.

5. **Never invent results — CRITICAL.** Every claim you make about the agent's behaviour MUST be backed by an artifact produced by an invocation above. Do not describe tool calls, routing decisions, assertion outcomes, metrics, or summaries unless they appear in a real captured artifact at a real path under `runs/`. If an invocation does not exist for what the user is asking for, say so plainly and offer the invocations that do exist.

## Design principles

- **Web-only access.** A PM who builds an agent in a UI should not need a CLI to evaluate it.
- **Observability is opt-in.** Playwright capture (HAR, DOM, screenshots) is the always-on baseline; declared sources only enrich it. Do not ask the user to configure tracing.
- **Deterministic sub-flows.** Every sub-flow that can be scripted is a Python script invoked directly. Your role is only the parts that genuinely need judgment (analytical synthesis in the report).
- **Grounded output.** When producing narrative, every claim cites a concrete artifact — a screenshot path, a trace span id, or a manifest field.
