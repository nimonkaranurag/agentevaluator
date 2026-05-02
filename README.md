<div align="center">

<br>

<img src="assets/agentevaluator-demo.gif" alt="agentevaluator in action" width="720">

<br><br>

**A [Claude Skill](https://support.claude.com/en/articles/12512176-what-are-skills) that interrogates your deployed agent so you don't have to 🔬**

<p align="center">
  <img src="https://media1.tenor.com/m/LK1Zig7TXBoAAAAd/batman-joker.gif" width="480">
</p>

---

</div>

<br>

## How to run this skill on an agent deployed on any agent runtime:

#### Step 1: Clone this repository

#### Step 2: 

```
> /onboard-evaluate-agent          ← answer a few questions, get an agent.yaml manifest, this describes the configuration for the eval run including the conversation trajectories that will/should be tested.
> /evaluate-agent                  ← sit back. claude does the rest.
```

## Quick Run using IBM's ADK. [*IBM ADK?*](https://developer.watson-orchestrate.ibm.com)

The repo ships with a ready-to-run example so you can see the full loop before wiring up your own agent:

- **[`hr-agent-watsonx-orchestrate`](.claude/skills/evaluate-agent/examples/hr-agent-watsonx-orchestrate/agent.yaml)**
→ Check the [walkthrough](.claude/skills/evaluate-agent/examples/hr-agent-watsonx-orchestrate/_resources/README.md) to see how it all connects.

#### Enable orchestrate's built-in Langfuse (one-time, local dev)

Orchestrate's Developer Edition ships with Langfuse built in but it's opt-in — start the server with the flag below so the four observability-driven assertions (`must_call`, `must_not_call`, `must_route_to`, `max_steps`) resolve to passed/failed instead of inconclusive:

```sh
orchestrate server start --with-langfuse        # -l also works
```

Local Langfuse UI lands at [`http://localhost:3010`](http://localhost:3010) (creds: `orchestrate@ibm.com` / `orchestrate`). Sign in, generate an API key pair (Settings → API Keys), export them as `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` in the shell that runs `/evaluate-agent`. Tool-call / agent-decision / generation spans are auto-emitted by orchestrate — no SDK wiring lives in your tools.

#### Happy-path testing/POC

![alt-text](./assets/demo-1.png) *ran against the onboarding manifest [here](.claude/skills/evaluate-agent/examples/hr-agent-watsonx-orchestrate/agent.yaml)*

<br>

![alt-text](./assets/demo-2.png) *exhaustive pre-flight check-list so validation errors/env misconfigurations are caught early*
![alt-text](./assets/demo-3.png) *claude orchestrates an agent swarm to execute different workflows/testing scenarios live on the deployed agent in parallel*

<br>

![alt-text](./assets/demo-4.png) *for IBM Orchestrate-lite, this means using playright to interact with the deployed agent through the ADK built-in Orchestrate ChatUI (basic, bare-bones integration POC)*




<br>

<div align="center">

---

<sub> UNDER CONSTRUCTION 🚧 · Powered by stubbornness and too much coffee ☕️</sub>

</div>
