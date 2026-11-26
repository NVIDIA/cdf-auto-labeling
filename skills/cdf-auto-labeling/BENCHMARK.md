# Skill Benchmark: cdf-auto-labeling

> ✅ **Overall verdict: PASS — Recommended for publication**

## Publication Recommendation

Recommended for publication based on the completed evaluation evidence in this report.

## Evaluation Metadata

- Skill: `cdf-auto-labeling`
- Validation status: `passed`
- Evaluation date: 2026-11-25
- Evaluator version: `1.6.10`
- Agents: Claude Code (`aws/anthropic/bedrock-claude-opus-5-5`), Codex (`openai/openai/gpt-6.1-sol`)
- Tasks: 4 evaluation tasks (4 positive)
- Dataset digest: `sha256:3716edfb86892785a41829de550b28bea9ac5f9cbbe5b2a2195741c8f6fb0b1c` (skill-evaluator-dataset-snapshot/1)
- Attempts per task: 1
- Environment: `k8s-sandbox`
- Tier 2 evidence: required for publication
- Tier 3 evidence: required for publication

Each task attempt ran in its own isolated sandbox pod.

## Tier 1 LLM Provenance

SkillSpector provider, model, analyzer revision, and determinism evidence retained for this scan.

| Skill | Provider | Adapter | Analyzer | Model | Revision | Determinism |
| --- | --- | --- | --- | --- | --- | --- |
| cdf-auto-labeling | nv_inference | openai | mcp_tool_poisoning | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.5` | nondeterministic / provider_defaults |
| cdf-auto-labeling | nv_inference | openai | semantic_developer_intent | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.5` | nondeterministic / provider_defaults |
| cdf-auto-labeling | nv_inference | openai | semantic_quality_policy | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.5` | nondeterministic / provider_defaults |
| cdf-auto-labeling | nv_inference | openai | semantic_security_discovery | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.5` | nondeterministic / provider_defaults |
| cdf-auto-labeling | nv_inference | openai | meta_analyzer | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.5` | nondeterministic / provider_defaults |

- Controls for `cdf-auto-labeling`: temperature=not set (source=provider_default, forwarded=no); seed=not set (source=unset, forwarded=no); reasoning_effort=not set (source=provider_default, forwarded=no)

## What This Report Answers

The three-tier evaluation checks whether the skill:

- is safe to use;
- produces correct answers;
- is discovered and activated when needed;
- helps the agent complete the user's goal and expected workflow; and
- avoids wasted skill and tool usage.

## Results at a Glance

| Measure | Claude Code (Baseline → Skill Uplift) | Codex (Baseline → Skill Uplift) |
|---|---:|---:|
| Overall | 95.4% — baseline ran, but no comparable score was available; uplift unavailable | 87.8% — baseline ran, but no comparable score was available; uplift unavailable |
| Security | 100.0% → 100.0% (±0.0 points) | 100.0% → 100.0% (±0.0 points) |
| Correctness | 35.0% → 100.0% (+65.0 points) | 45.0% → 90.0% (+45.0 points) |
| Discoverability | 99.0% — baseline ran, but no comparable score was available; uplift unavailable | 93.8% — baseline ran, but no comparable score was available; uplift unavailable |
| Effectiveness | 14.0% → 82.5% (+68.5 points) | 20.2% → 65.8% (+45.6 points) |
| Efficiency | 95.5% — baseline ran, but no comparable score was available; uplift unavailable | 89.4% — baseline ran, but no comparable score was available; uplift unavailable |

**How to read this table:** baseline is the same task attempted without the target skill. Scores are rounded to one decimal; threshold-adjacent values use additional precision so their displayed band matches the verdict. Uplift is derived from those displayed scores and shown in percentage points.

Example: `47.0% → 92.0% (+45.0 points)` means the skill-assisted run scored 92.0%, 45.0 percentage points above its 47.0% no-skill baseline.

### Comparison details

Shared-source comparisons use the same signals and weights on both conditions. They do not replace the full dimension scores above or change the publication verdict.

| Agent | Dimension | Basis | Baseline → With skill (uplift) | Explanation |
| --- | --- | --- | --- | --- |
| claude-code | Discoverability | Dimension comparison | N/A | Discoverability is not applicable to the no-skill baseline; there is no installed skill to discover. |
| claude-code | Efficiency | Token-only comparison | 98.4% → 96.1% (-2.3 points) | Only Token Efficiency is comparable; the full dimension scores use different evaluator sources. |
| codex | Discoverability | Dimension comparison | N/A | Discoverability is not applicable to the no-skill baseline; there is no installed skill to discover. |
| codex | Efficiency | Token-only comparison | 92.0% → 91.3% (-0.7 points) | Only Token Efficiency is comparable; the full dimension scores use different evaluator sources. |

## Token Usage

Actual Tier 3 execution usage is reported for every observed agent/case pair and both conditions.

| Agent | Dataset case | With skill | Without skill | Delta | Change | Coverage |
|---|---|---:|---:|---:|---:|---|
| claude-code | All cases | 616,865 | 464,831 | +152,034 | +32.71% | skill 4/4; base 4/4 |
| claude-code | 1 | 192,733 | 107,331 | +85,402 | +79.57% | skill 1/1; base 1/1 |
| claude-code | 2 | 74,201 | 107,648 | -33,447 | -31.07% | skill 1/1; base 1/1 |
| claude-code | 3 | 234,930 | 142,751 | +92,179 | +64.57% | skill 1/1; base 1/1 |
| claude-code | 4 | 115,001 | 107,101 | +7,900 | +7.38% | skill 1/1; base 1/1 |
| codex | All cases | 179,418 | 202,842 | -23,424 | -11.55% | skill 4/4; base 4/4 |
| codex | 1 | 29,266 | 54,714 | -25,448 | -46.51% | skill 1/1; base 1/1 |
| codex | 2 | 28,880 | 54,594 | -25,714 | -47.10% | skill 1/1; base 1/1 |
| codex | 3 | 67,575 | 40,684 | +26,891 | +66.10% | skill 1/1; base 1/1 |
| codex | 4 | 53,697 | 52,850 | +847 | +1.60% | skill 1/1; base 1/1 |
| ALL AGENTS | Dataset aggregate | 796,283 | 667,673 | +128,610 | +19.26% | skill 8/8; base 8/8 |

Prompt tokens include cached reads, so total tokens are `prompt + completion` (cached is not added twice). The Efficiency score uses `(prompt - cached) + completion`. Change is `100 * (with - without) / without`; negative means fewer tokens. N/A comparisons include their reason in the coverage column; coverage is never estimated.

## Tier Status

| Tier | Purpose | Status | Evidence |
|---|---|---|---|
| Tier 1 | Static validation | **PASSED WITH OBSERVATIONS** | 11 validator(s); 11 finding(s) |
| Tier 2 | Semantic deduplication | **PASSED WITH OBSERVATIONS** | 2 validator(s); 5 finding(s) |
| Tier 3 | Live agent evaluation | **PASS** | 2 agent(s); 4 task(s) |

## Findings and Observations

<details>
<summary>Show detailed findings and successful checks</summary>

- **HIGH** DUPLICATE/duplicate: Duplicate content found across references/stages/captioning.md and references/stages/visual-qa.md:
  "## Video payload mode and Cosmos" in references/stages/captioning.md (lines 86-102)
  vs "## Video payload mode and Cosmos" in references/stages/visual-qa.md (lines 135-151) (`references/stages/captioning.md:86`)
- **HIGH** DUPLICATE/duplicate: Duplicate content found across references/scenario-planning/pipeline-composition.md and references/workflow-stage-integration/stage-service-contract.md:
  "## Data Flow Contract" in references/scenario-planning/pipeline-composition.md (lines 159-176)
  vs "## Data And Sidecar Contract" in references/workflow-stage-integration/stage-service-contract.md (lines 33-49) (`references/scenario-planning/pipeline-composition.md:159`)
- **HIGH** DUPLICATE/duplicate: Duplicate content found across references/workflow-runner-debugging.md and references/workflow-runner-debugging/runner-debugging-patterns.md:
  "# Inspect stage commands (runner container only)" in references/workflow-runner-debugging.md (lines 78-81)
  vs "## Runner Commands" in references/workflow-runner-debugging/runner-debugging-patterns.md (lines 12-35) (`references/workflow-runner-debugging.md:78`)
- **HIGH** DUPLICATE/duplicate: Duplicate content found across references/stages/grounding-2d-patterns.md and references/stages/grounding-2d.md:
  "## Images and orchestration" in references/stages/grounding-2d-patterns.md (lines 25-31)
  vs "## Packaging" in references/stages/grounding-2d.md (lines 13-28) (`references/stages/grounding-2d-patterns.md:25`)
- **HIGH** DUPLICATE/duplicate: Duplicate content found across references/stages/detection-and-tracking.md and references/stages/detection-tracking-patterns.md:
  "## Inputs -> Outputs" in references/stages/detection-and-tracking.md (lines 79-87)
  vs "## Data Flow" in references/stages/detection-tracking-patterns.md (lines 58-76) (`references/stages/detection-and-tracking.md:79`)
- 11 additional finding(s) are available in the full evaluation artifacts.

</details>

## Scoring Methodology

<details>
<summary>Show dimension definitions, source signals, and thresholds</summary>

| Dimension | Question | Scored signals |
|---|---|---|
| Security | Is it safe to use? | `security` (100%) |
| Correctness | Is the answer correct? | `accuracy` (100%) |
| Discoverability | Was the right skill loaded when needed? | `skill_execution` (100%) |
| Effectiveness | Did the skill help complete the task? | `goal_accuracy` (50%) + `behavior_check` (50%) |
| Efficiency | Did it avoid wasted tool calls and token usage? | `skill_efficiency` (50%) + `token_efficiency` (50%) |

- Dimension bands: PASS at 50% or above; NEUTRAL from 40% to below 50%; FAIL below 40%.
- Overall Tier 3 lift: PASS at +5 points or more; FAIL at -10 points or less; values between those bands are NEUTRAL.
- Overall verdict: PASS only when every configured dimension passes for at least one supported agent. Lift is reported as diagnostic evidence and does not override this gate.
- The 50% attempt pass threshold is a separate per-task gate; it is not the dimension pass threshold.
- Effectiveness is the equal-weight mean of goal completion (`goal_accuracy`) and expected workflow adherence (`behavior_check`).
- Efficiency is 50% tool-call productivity (the backward-compatible `skill_efficiency` wire id) and 50% `token_efficiency`. Positive-case skill routing is scored under Discoverability, not Efficiency; a negative case without a routing target is N/A. N/A sources are omitted, remaining weights are renormalized, and the dimension is marked partial.

Signals present in this run:

- `security` (Security): unsafe operations, secret leakage, and unauthorized access.
- `skill_execution` (Skill Execution): whether the expected skill was selected, decoys were avoided, and the workflow executed.
- `skill_efficiency` (Tool Productivity): tool-call productivity (legacy wire id; routing is scored under Discoverability).
- `accuracy` (Accuracy): final-answer correctness against the reference answer.
- `goal_accuracy` (Goal Accuracy): whether the user's goal was achieved.
- `behavior_check` (Behavior Check): whether the expected workflow behavior was followed.
- `token_efficiency` (Token Efficiency): actual uncached prompt plus completion usage (50% of Efficiency).

</details>

## Freshness

Regenerate this benchmark when the skill, evaluation dataset, target agent/model, evaluator version, environment, or scoring policy changes.
