# People Directory demo — orchestrate import resources

Files in this directory are the **agent under evaluation**, not part of
agentevaluator. They define a tiny watsonx Orchestrate agent the parent
`agent.yaml` manifest then drives end to end via the Playwright MCP server.
Tool calls / agent decisions / generations are observed by orchestrate's
built-in LangFuse integration — not by SDK wrapping in the toolkit.

## Layout

```
_resources/
├── agents/
│   └── people_directory_agent.yaml   # native orchestrate agent definition
├── tools/
│   └── people_directory_tools.py     # 3 native python tools, in-memory data
└── import_all.sh                     # idempotent UX-friendly importer
```

## End-to-end workflow

### 1. Start the orchestrate dev server with Langfuse

```sh
orchestrate server start --with-langfuse     # -l also works
orchestrate env activate local
```

The `--with-langfuse` flag brings up a local Langfuse instance at
[`http://localhost:3010`](http://localhost:3010) (creds:
`orchestrate@ibm.com` / `orchestrate`). Orchestrate auto-instruments
every tool call, agent decision, and LLM generation so the four
observability-driven assertions in the manifest resolve to passed/failed
instead of inconclusive.

### 2. Generate Langfuse API keys + export them

Sign in to the local Langfuse UI, open **Settings → API Keys**, create a
new key pair, then export the values into the shell that will run the
agentevaluator's `fetch_observability.py`:

```sh
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
```

The manifest's `observability.langfuse` block names these env-var names;
no secret is ever written into a file.

### 3. Import the demo agent + tools

```sh
./_resources/import_all.sh
```

The script is idempotent — re-running is safe. It pre-flights the
orchestrate CLI, the active env, the resource files, and the local
Langfuse reachability before invoking the import.

### 4. Hand the manifest to the evaluator

```sh
orchestrate chat start                    # serves the chat UI on :3000
```

In Claude Code, from the repo root:

```
> /evaluate-agent
```

Claude:

- discovers the manifest in this directory (or you point it at the path);
- opens the chat URL in a Playwright MCP browser window you can watch;
- runs the manifest's precondition (`select #selected-agent-dropdown` → `people_directory_agent`) so the right agent is bound to the chat input;
- types `case.input` and waits the declared `response_wait_ms`;
- saves the landing + post-submit screenshots and DOM snapshots under `runs/<agent>/<run_id>/<case_id>/`;
- runs `fetch_observability.py` to pull the orchestrate-emitted Langfuse traces from `http://localhost:3010` into `trace/observability/`;
- scores every assertion;
- synthesizes a per-case narrative whose every claim cites a real captured artifact;
- renders the final Markdown report.

For the swarm path (every declared case in parallel), Claude runs `plan_swarm.py` first and dispatches one Agent sub-task per directive in a single message — each sub-task is assigned a unique Playwright MCP pool slot from the repo's `.mcp.json` and drives its case in its own browser context.

## Notes

- **The local Langfuse host (`http://localhost:3010`) is hard-coded in the manifest.** If you point orchestrate at a hosted Langfuse via `orchestrate settings observability langfuse configure --url ...`, edit the manifest's `observability.langfuse.host` to match.