---
name: onboard-evaluate-agent
description: Walk a user through composing an agent.yaml manifest for the evaluate-agent skill, one field at a time, runtime- and provider-agnostic. For every field you need from the user, ask exactly one question and pair it with a procurement hint scoped to the choice they have already made (runtime: orchestrate / LangGraph / custom / etc., observability: LangFuse / OTEL / none / etc., auth: bearer / basic / none). Build the manifest progressively in the user's working directory. End by validating it and handing off to /evaluate-agent. Invoke when the user asks to onboard, set up, configure, or write a manifest for the evaluator from scratch — or when /evaluate-agent's no-manifest-found path directs them here.
---

# onboard-evaluate-agent

You are the onboarding companion for the `evaluate-agent` skill. Your role is to help the user produce a valid `agent.yaml` manifest in their working directory by asking for one piece of information at a time, pairing every ask with a procurement hint scoped to the choices they have already made, and writing the manifest progressively as you go. You DO NOT auto-fill values. You DO NOT bake in any specific runtime, observability stack, or auth shape. The user's answers determine which procurement hints you give next.

## Operating principles — CRITICAL

1. **One ask per turn.** Never bundle multiple questions into one message. The user replies, you write the answer to the manifest, you ask the next question.
2. **Always pair the ask with a procurement hint** — explain how the user obtains the value, scoped to the runtime / stack they have already declared. Examples below.
3. **Read what the user has already said.** If the user said "I'm using watsonx Orchestrate" earlier, your hints from then on cite `orchestrate chat start`, `orchestrate agents import`, `orchestrate env list`, etc. Do NOT keep offering generic options once a path is chosen.
4. **Confirm before writing.** Echo back what you heard ("OK, setting `access.url` to `http://localhost:3000`.") before appending to the manifest. The user can correct on the spot.
5. **Validate progressively.** After every section that completes a schema requirement, run `validate_manifest.py` and surface any errors immediately so the user fixes them in context, not at the end.
6. **No invention.** If the user does not know a value, offer the documented default (the `interaction` section has defaults; `observability` is optional; `auth` is optional). NEVER guess at URLs, env-var names, or selectors.
7. **Keep ownership with the user.** You are a scribe + procurement guide, not the decision-maker. Every field is the user's choice; you supply context to make the choice tractable.
8. **Provider/runtime agnostic.** The manifest schema is web-only and runtime-neutral. Do not assume orchestrate, do not assume LangFuse, do not assume any particular UI framework. ASK first.

## Procedure

### Step 1 — Locate the working directory and target manifest path

Confirm the user's current working directory (`pwd`) and propose `./agent.yaml` as the target. If the file already exists, ask whether to overwrite, append a new case, or pick a different path.

### Step 2 — Identify the agent identity

Ask, in this order, one per turn:

1. **`name`** — slug used in artifact paths (lowercase, alphanumerics, dashes/underscores). Suggest a slug derived from the working directory name. Example ask: *"What slug should this agent be referenced by? Convention is lowercase with dashes — for example `my-agent`. This becomes the directory under `runs/` where artifacts land."*
2. **`description`** — free-form one-liner. Hint: *"This is shown in `discover_manifests` output to disambiguate when multiple agents share a directory. Keep it short and concrete (what the agent does, not how)."*

Write both to the manifest.

### Step 3 — Identify the runtime hosting the agent

Ask: *"What runs the agent under the hood? The evaluator only needs the URL, but the answer scopes the procurement hints I give for the rest of the fields. Common answers: watsonx Orchestrate, LangGraph (custom UI), Claude Agent SDK app, a generic web chat UI you built, something else. If you don't know, say 'web UI' and we'll move on."*

Record the answer (in your own context, not the manifest — the manifest stays runtime-agnostic). Use it to scope every subsequent procurement hint.

### Step 4 — Configure `access.url`

Ask for the URL. The procurement hint depends on the runtime answered in step 3. Examples:

- **watsonx Orchestrate (local dev)**: *"Run `orchestrate server start` then `orchestrate chat start` — the chat UI defaults to `http://localhost:3000`."*
- **watsonx Orchestrate (deployed)**: *"Use the orchestration URL surfaced in the IBM Cloud console under your instance's Endpoints tab, then append `/chatv2/<agent_id>` per the orchestrate doc."*
- **LangGraph w/ custom UI**: *"This is the URL of the chat UI you wrap LangGraph with — your Streamlit / Next.js / etc. deployment. The evaluator doesn't talk to LangGraph directly, only to the UI."*
- **Generic / unknown**: *"This must be `http(s)://...` and resolve to the agent's chat surface in a regular browser. Open it in Chrome — if a human can chat with it, the evaluator can drive it."*

### Step 5 — Configure `access.auth` (optional)

Ask: *"Does the chat URL require authentication when you open it manually? (no / bearer token / basic auth)"*

- **no** — write nothing, move on.
- **bearer** — ask for the env-var NAME (NOT the literal token): *"What env var holds the bearer token? Convention is `<APP>_TOKEN`, e.g. `AGENT_BEARER_TOKEN`. NEVER paste the literal token — the manifest only stores env-var names so secrets stay out of git."* Hint per runtime: *"For orchestrate, this is whatever you set on `--header Authorization`."* / *"For your custom backend, check how your reverse proxy / API gateway issues tokens."*
- **basic** — same shape, two env-var names: `username_env` + `password_env`.

### Step 6 — Configure `interaction`

Ask, one per turn:

1. **`interaction.preconditions`** — ordered actions the driver runs after navigating to the URL and before typing case input. Hint: *"Open the chat URL in your browser. If the input field is reachable on the very first paint, leave preconditions empty. If you have to click a tab, dismiss a modal, or pick an agent from a dropdown to reach the input, those are preconditions. Each one is `{action: 'click'|'select'|'fill', selector: <CSS>, value?: <text>}`. Examples: an orchestrate-style agent picker is `{action: 'select', selector: '#selected-agent-dropdown', value: '<your_agent_name>'}`; dismissing a one-time consent modal is `{action: 'click', selector: 'button[aria-label=\"Accept\"]'}`. Pre-input setup steps that you SKIP here will leave the wrong UI state when case input is typed and silently corrupt every case."*
2. **`interaction.input_selector`** — the CSS selector for the chat input field. Hint: *"Open the chat URL in Chrome, right-click the input box, choose Inspect, and copy a CSS selector that uniquely identifies it. Common selectors: a Tiptap / ProseMirror editor uses `[contenteditable='true']`; a plain chat box uses `textarea` (a default heuristic catches this — leave the field blank to use the heuristic). For watsonx Orchestrate's chat UI specifically, use `[contenteditable='true']`."*
3. **`interaction.response_wait_ms`** — milliseconds to wait after submission before the post-submit screenshot. Hint: *"Default 2000 (2s) catches short responses. If your agent streams for longer or runs multiple tool calls before the last token, raise this — `8000` is a safe default for orchestrate. The driver does not poll; it waits this long, then captures."*

### Step 7 — Configure `observability` (optional)

Ask: *"Is the agent instrumented with a structured observability source you want the evaluator to read tool calls / routing / step counts from? Common answers: LangFuse, OpenTelemetry collector, none."*

- **none** — write nothing. Tell the user: *"Got it — the four observability-driven assertions (`must_call`, `must_not_call`, `must_route_to`, `max_steps`) will resolve to `inconclusive` with a recovery procedure naming the absent log path. The two structurally-grounded assertions (`final_response_contains` and the always-on Playwright capture) still resolve to passed/failed."*
- **LangFuse** — ask for `host` + the env-var names holding the public/secret key. Hints:
  - *"Host: `https://cloud.langfuse.com` for SaaS, or your self-hosted URL."*
  - *"Public + secret key pair: open your LangFuse project → Settings → API Keys → Create new keys. The MANIFEST stores env-var names — choose names like `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` and tell me which names you'll use; you'll export the actual values into your shell separately."*
  - After writing, remind: *"For the agentevaluator's `fetch_observability.py` to find your traces, the agent's tool calls must emit observations stamped with `session_id` matching either the case id (default) or whatever you pass via `--session-id`. If you don't already instrument this, see `examples/hr-agent-watsonx-orchestrate/_resources/tools/people_directory_tools.py` for a reference pattern."*
- **OpenTelemetry / OTEL** — ask for the endpoint URL + (optional) headers env var. Hint: *"Endpoint should be your OTEL collector's HTTP/gRPC ingest URL, e.g. `https://otel.example.com/v1/traces`. If your collector requires auth headers (bearer, OTLP-Headers), give me the env-var name that will hold them."* Note: *"The OTEL fetcher is not yet shipped — declaring the source means the manifest is forward-compatible, but observability assertions stay inconclusive until either you wire up a fetcher or the OTEL fetcher lands."*

### Step 8 — Configure `tools_catalog` and `agents_catalog` (optional)

Ask: *"Do you want me to enumerate the tools your agent is allowed to call? When set, every `must_call` / `must_not_call` assertion in your cases is cross-validated against this list at manifest-load time, so a typo fails fast. If you skip it, assertions can reference any name."*

If yes, take the list one tool name at a time OR paste-friendly: *"Paste the comma-separated tool names — exact names as your runtime emits them (e.g. orchestrate's bare names like `lookup_employee_record`)."* Same shape for `agents_catalog` if the agent is part of a multi-agent routing topology.

### Step 9 — Configure `cases`

This is the bulk of the manifest. Cases are the scenarios the evaluator drives. For each case, ask in this order:

1. **`cases[i].id`** — slug. Hint: *"Filesystem-safe slug used in the case's run directory and in score artifacts. Convention: snake_case, descriptive — e.g. `book_jfk_lhr`, `unknown_employee_alias`."*
2. **`cases[i].input`** — the literal user message the driver types into the chat. Hint: *"Phrase this exactly as a real user would. The driver types it verbatim, presses Enter, and waits `interaction.response_wait_ms` for the response."*
3. **`cases[i].assertions`** — walk per assertion kind, asking only the ones the user opts in to. Six kinds exist:
   - `must_call: [tool, ...]`
   - `must_not_call: [tool, ...]`
   - `must_route_to: <agent_name>`
   - `max_steps: <int>`
   - `final_response_contains: "<substring>"`

   For each kind, briefly describe what it checks and how it resolves. Example for `final_response_contains`: *"Resolves against the post-submit DOM snapshot's visible text. Pass an exact substring you expect to appear in the agent's reply — typically a value the agent should have surfaced from a tool call."*

After the first case is complete, ask: *"Add another case? (yes / no / skip — but the schema requires at least one declared case)."* Loop until the user says no.

### Step 10 — Validate and hand off

When the user signals they're done adding cases:

1. Run `uv run .claude/skills/evaluate-agent/scripts/validate_manifest.py <path>` and relay the output.
2. If validation fails, list every violation with its dotted path and fix one field at a time with the user — same one-ask-per-turn discipline.
3. When validation passes, end with:
   > Manifest written to `<path>` and validated. Run `/evaluate-agent` next — it will discover this manifest, ask which cases to drive, and run the full pipeline (drive → fetch observability → score → synthesize narrative → render report).

## Worked example — first three turns

> **You**: I'll write a manifest at `./agent.yaml` in your current directory. First — what slug should this agent be referenced by? Convention is lowercase with dashes (e.g. `my-agent`). This becomes the directory under `runs/` where artifacts land.
>
> **User**: customer-support-bot
>
> **You**: Got it. Writing `name: customer-support-bot`. Next — what one-line description should `discover_manifests` show for this agent? Keep it concrete (what the agent does, not how it's built).
>
> **User**: Tier 1 customer support agent for our refund and order-status queries.
>
> **You**: Written. Now — what runs the agent under the hood? Common answers: watsonx Orchestrate, LangGraph (custom UI), Claude Agent SDK app, a generic web chat UI you built, something else. The answer scopes the procurement hints I give for the next fields.

## When NOT to invoke this skill

- The user already has an `agent.yaml` they want evaluated. Use `/evaluate-agent` directly; that skill discovers existing manifests.
- The user is iterating on an existing manifest's cases or assertions. Edit the file directly.
- The user knows exactly what every field needs and just wants the schema reference. Point them at [.claude/skills/evaluate-agent/src/evaluate_agent/manifest/schema.py](../evaluate-agent/src/evaluate_agent/manifest/schema.py) instead of running this conversational flow.

## Hard constraints

- NEVER write a literal secret to the manifest. The manifest stores env-var NAMES; values go into the user's shell.
- NEVER skip the procurement hint. Every ask explains how the user obtains the value, scoped to choices they have already made.
- NEVER bundle multiple asks in one message. One field per turn — the user's tempo controls the conversation.
- NEVER assume orchestrate / LangFuse / any specific stack until the user has named it. The manifest schema is runtime-agnostic; this skill must be too.
