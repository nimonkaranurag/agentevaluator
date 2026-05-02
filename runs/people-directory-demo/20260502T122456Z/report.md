# Agent evaluation report — `people-directory-demo`

**Run id:** `20260502T122456Z`
**Manifest:** `/Users/nimo/Desktop/personal-dev/agentevaluator/.claude/skills/evaluate-agent/examples/hr-agent-watsonx-orchestrate/agent.yaml`
**Runs root:** `/Users/nimo/Desktop/personal-dev/agentevaluator/runs`

## Summary

| Metric | Total | Passed | Failed | Inconclusive |
| --- | ---: | ---: | ---: | ---: |
| Assertions | 25 | 5 | 0 | 20 |

## By assertion kind

| Kind | Total | Passed | Failed | Inconclusive |
| --- | ---: | ---: | ---: | ---: |
| `final_response_contains` | 5 | 5 | 0 | 0 |
| `must_call` | 10 | 0 | 0 | 10 |
| `must_not_call` | 5 | 0 | 0 | 5 |
| `max_steps` | 5 | 0 | 0 | 5 |

## By target

| Kind | Target | Total | Passed | Failed | Inconclusive |
| --- | --- | ---: | ---: | ---: | ---: |
| `must_call` | `list_direct_reports` | 2 | 0 | 0 | 2 |
| `must_call` | `list_paid_leave_days` | 3 | 0 | 0 | 3 |
| `must_call` | `lookup_employee_record` | 5 | 0 | 0 | 5 |
| `must_not_call` | `list_direct_reports` | 3 | 0 | 0 | 3 |
| `must_not_call` | `list_paid_leave_days` | 2 | 0 | 0 | 2 |

## By case

| Total | Fully passed | With any failure | With any inconclusive | With no assertions |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 0 | 0 | 5 | 0 |

## Per-case detail

### Case `timeoff_for_known_employee` — 1 passed, 0 failed, 4 inconclusive (of 5 total)

**Directory:** `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_for_known_employee`

**Assertion outcomes:**

- **PASSED** `final_response_contains`
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_for_known_employee/trace/dom/step-002-after_submit.html`
  - Detail: matched substring at character offset 979 of extracted visible text; surrounding excerpt: 'Directory Demo 1:29 PM Show Reasoning Step 1 Step 2 alex.river took time off on 20260118 between 2026-01-01 and 2026-03-31. Good response Bad response Copy Additional f'

- **INCONCLUSIVE** `must_call` — target `lookup_employee_record`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_call` — target `list_paid_leave_days`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_not_call` — target `list_direct_reports`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `max_steps`
  - Reason: `observability_source_missing`
  - Needed evidence: `step_count`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

#### Analytical narrative

The agent answered the date-bounded time-off question for alex.river, returning a single dated leave entry inside the requested window. The visible response in the post-submit DOM matches the manifest's final_response_contains assertion, so the user-facing behavior is correct. The four observability-driven assertions (must_call lookup_employee_record, must_call list_paid_leave_days, must_not_call list_direct_reports, max_steps) cannot be resolved because LangFuse credentials were not exported during the run, so no tool_calls.jsonl or step_count.json was landed under trace/observability/.

##### Observations

- **success_mode** — The post-submit DOM contains the visible reply 'alex.river took time off on 20260118 between 2026-01-01 and 2026-03-31.', satisfying the final_response_contains assertion.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_for_known_employee/trace/dom/step-002-after_submit.html` (locator: character offset 979 in extracted visible text)

- **behavior** — The post-submit screenshot shows the agent rendered a Step 1 / Step 2 reasoning trail before emitting the final answer, consistent with a multi-step tool-using flow.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_for_known_employee/step-002-after_submit.png` (locator: Show Reasoning panel)

- **failure_mode** — Tool-use and step-count assertions resolved to inconclusive because LangFuse credentials were not exported, so no observability logs were fetched into trace/observability/ for the captured DOM to be correlated against.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_for_known_employee/step-001-landing.png` (locator: landing state baseline)

### Case `timeoff_with_multiple_days_in_range` — 1 passed, 0 failed, 4 inconclusive (of 5 total)

**Directory:** `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_with_multiple_days_in_range`

**Assertion outcomes:**

- **PASSED** `final_response_contains`
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_with_multiple_days_in_range/trace/dom/step-002-after_submit.html`
  - Detail: matched substring at character offset 1041 of extracted visible text; surrounding excerpt: 'f between 2026-01-01 and 2026-04-30 was on the following days: [\\"20260218\\", \\"20260301\\"]. Good response Bad response Copy Additional feedback What makes you give thi'

- **INCONCLUSIVE** `must_call` — target `lookup_employee_record`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_call` — target `list_paid_leave_days`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_not_call` — target `list_direct_reports`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `max_steps`
  - Reason: `observability_source_missing`
  - Needed evidence: `step_count`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

#### Analytical narrative

The agent returned both expected leave dates for jordan.kim within the four-month window as a JSON-style list, satisfying the final_response_contains assertion via the post-submit DOM. The remaining four observability-driven assertions are inconclusive because LangFuse credentials were not exported and no trace/observability/ files were landed under the case directory; the agent's actual tool sequence and step count cannot be confirmed from the captured DOM alone.

##### Observations

- **success_mode** — The post-submit DOM contains the visible reply enumerating both expected leave days, ['20260218', '20260301'], satisfying the final_response_contains assertion.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_with_multiple_days_in_range/trace/dom/step-002-after_submit.html` (locator: character offset 1041 in extracted visible text)

- **behavior** — The post-submit screenshot shows the agent enumerated multiple dates in a structured list inside the response bubble, consistent with a list-paid-leave-days tool result being formatted into the final reply.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_with_multiple_days_in_range/step-002-after_submit.png` (locator: agent response bubble)

- **failure_mode** — must_call lookup_employee_record, must_call list_paid_leave_days, must_not_call list_direct_reports, and max_steps all resolved to inconclusive because no observability logs were fetched into trace/observability/ during the run.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/timeoff_with_multiple_days_in_range/step-001-landing.png` (locator: landing state baseline)

### Case `manager_direct_reports` — 1 passed, 0 failed, 4 inconclusive (of 5 total)

**Directory:** `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_direct_reports`

**Assertion outcomes:**

- **PASSED** `final_response_contains`
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_direct_reports/trace/dom/step-002-after_submit.html`
  - Detail: matched substring at character offset 796 of extracted visible text; surrounding excerpt: 'ry Demo 1:29 PM Show Reasoning Step 1 Step 2 The direct reports of sam.cole are alex.river and jordan.kim. Good response Bad response Copy Additional feedback What makes '

- **INCONCLUSIVE** `must_call` — target `lookup_employee_record`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_call` — target `list_direct_reports`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_not_call` — target `list_paid_leave_days`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `max_steps`
  - Reason: `observability_source_missing`
  - Needed evidence: `step_count`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

#### Analytical narrative

The agent identified both expected direct reports of sam.cole (alex.river and jordan.kim), satisfying the final_response_contains assertion against the post-submit DOM. The supporting tool-use assertions (must_call lookup_employee_record, must_call list_direct_reports, must_not_call list_paid_leave_days) and the max_steps bound are inconclusive because LangFuse observability was not fetched, so the underlying tool-call sequence cannot be verified from the captured DOM alone.

##### Observations

- **success_mode** — The post-submit DOM contains the visible reply 'The direct reports of sam.cole are alex.river and jordan.kim.', satisfying the final_response_contains assertion.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_direct_reports/trace/dom/step-002-after_submit.html` (locator: character offset 796 in extracted visible text)

- **behavior** — The post-submit screenshot shows a Step 1 / Step 2 reasoning trail above the response, consistent with the agent first looking up sam.cole and then enumerating their direct reports.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_direct_reports/step-002-after_submit.png` (locator: Show Reasoning panel)

- **failure_mode** — All four tool-use and step-count assertions resolved to inconclusive because the trace/observability/ directory was not populated for this case.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_direct_reports/step-001-landing.png` (locator: landing state baseline)

### Case `manager_team_timeoff_fanout` — 1 passed, 0 failed, 4 inconclusive (of 5 total)

**Directory:** `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_team_timeoff_fanout`

**Assertion outcomes:**

- **PASSED** `final_response_contains`
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_team_timeoff_fanout/trace/dom/step-002-after_submit.html`
  - Detail: matched substring at character offset 1020 of extracted visible text; surrounding excerpt: 'Reasoning Step 1 Step 2 Step 3 Step 4 Step 5 Step 6 Alex.river took time off on 20260118 and Jordan.kim took time off on 20260218 and 20260301. Good response Bad respon'

- **INCONCLUSIVE** `must_call` — target `lookup_employee_record`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_call` — target `list_direct_reports`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_call` — target `list_paid_leave_days`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `max_steps`
  - Reason: `observability_source_missing`
  - Needed evidence: `step_count`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

#### Analytical narrative

The agent successfully fanned out from sam.cole to her direct reports and aggregated each report's time off in the requested window into a single answer, satisfying the final_response_contains assertion. The post-submit screenshot reveals a six-step reasoning trail consistent with a multi-tool plan (resolve manager, list reports, query each report's leave). The four observability-driven assertions are inconclusive because LangFuse credentials were not exported, so the actual tool sequence and step count cannot be confirmed from the captured DOM alone.

##### Observations

- **success_mode** — The post-submit DOM contains the visible reply 'Alex.river took time off on 20260118 and Jordan.kim took time off on 20260218 and 20260301.', satisfying the final_response_contains assertion.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_team_timeoff_fanout/trace/dom/step-002-after_submit.html` (locator: character offset 1020 in extracted visible text)

- **behavior** — The post-submit screenshot displays a Step 1 through Step 6 reasoning trail above the final reply, consistent with a fan-out plan that resolves the manager, lists their direct reports, then queries each report's time off in turn.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_team_timeoff_fanout/step-002-after_submit.png` (locator: Show Reasoning panel — six steps)

- **failure_mode** — The three must_call assertions and the max_steps bound (declared at 8 in the manifest) resolved to inconclusive because no observability logs were fetched; the visible six-step trail in the screenshot is not the same evidence the scoring layer requires.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/manager_team_timeoff_fanout/step-001-landing.png` (locator: landing state baseline)

### Case `unknown_employee_alias` — 1 passed, 0 failed, 4 inconclusive (of 5 total)

**Directory:** `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/unknown_employee_alias`

**Assertion outcomes:**

- **PASSED** `final_response_contains`
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/unknown_employee_alias/trace/dom/step-002-after_submit.html`
  - Detail: matched substring at character offset 773 of extracted visible text; surrounding excerpt: "ple Directory Demo 1:27 PM Show Reasoning Step 1 Error: alias 'mira.unknown' is not registered in the directory. Good response Bad response Copy Additional feedback What make"

- **INCONCLUSIVE** `must_call` — target `lookup_employee_record`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_not_call` — target `list_paid_leave_days`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `must_not_call` — target `list_direct_reports`
  - Reason: `observability_source_missing`
  - Needed evidence: `tool_call_log`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

- **INCONCLUSIVE** `max_steps`
  - Reason: `observability_source_missing`
  - Needed evidence: `step_count`
  - Recovery: To proceed: declare an observability source under manifest.observability (langfuse for tool_call_log and routing_decision_log; otel for step_count) and confirm the agent under evaluation emits the corresponding spans. Land the structured log at the expected_artifact_path. Re-run the case with --submit and re-score.

#### Analytical narrative

The agent gracefully declined an out-of-directory alias by surfacing a structured 'not registered' error rather than fabricating a leave balance, satisfying the final_response_contains assertion. This is the desirable failure mode for an unknown-alias scenario. The supporting must_call lookup_employee_record assertion (the agent should have at least attempted the lookup) and the must_not_call assertions for list_paid_leave_days and list_direct_reports (the agent must NOT have called those after the lookup failed) are inconclusive because no observability logs were fetched. The screenshot shows only one reasoning step, which is consistent with an early exit on a failed lookup, but cannot substitute for the structured tool_calls.jsonl the scoring layer reads.

##### Observations

- **success_mode** — The post-submit DOM contains the visible reply "Error: alias 'mira.unknown' is not registered in the directory.", satisfying the final_response_contains assertion and demonstrating refusal-rather-than-hallucinate behavior on the unknown alias.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/unknown_employee_alias/trace/dom/step-002-after_submit.html` (locator: character offset 773 in extracted visible text)

- **behavior** — The post-submit screenshot shows only a single reasoning step before the error message, consistent with an early-exit on a failed employee-record lookup rather than a continued multi-tool plan.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/unknown_employee_alias/step-002-after_submit.png` (locator: Show Reasoning panel — single Step 1)

- **failure_mode** — must_call lookup_employee_record and must_not_call (list_paid_leave_days, list_direct_reports) resolved to inconclusive because the captured DOM cannot prove which tools were or were not invoked; resolution requires the trace/observability/tool_calls.jsonl that LangFuse fetch would have produced.
  - Evidence: `/Users/nimo/Desktop/personal-dev/agentevaluator/runs/people-directory-demo/20260502T122456Z/unknown_employee_alias/step-001-landing.png` (locator: landing state baseline)
