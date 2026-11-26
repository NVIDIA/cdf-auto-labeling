## Description: <br>
Use when a user needs to get started with CDF Auto-Labeling, plan a scenario, run or debug a shipped cookbook, author prompts or cookbooks, migrate a pipeline, configure a stage, or pull the prebuilt stage containers from NGC (nvcr.io). <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers use this skill to onboard to CDF Auto-Labeling and to plan, configure, run, debug, and extend cookbook-driven containerized pipelines that pseudo-annotate image and video datasets and export training-ready outputs. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [Yes] <br>
**Credential Type(s):** [API key] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [CDF Auto-Labeling Skill References](references/README.md) <br>
- [CDF Auto-Labeling Cookbook Authoring](references/cookbook-authoring.md) <br>
- [CDF Auto-Labeling Cookbook Schema](references/cookbook-authoring/cookbook-schema.md) <br>
- [Scenario Authoring](references/cookbook-authoring/scenario-authoring.md) <br>
- [CDF Visual Attribute Search](references/event-and-person-attribute-search.md) <br>
- [Visual Attribute Search run reference](references/event-and-person-attribute-search/run-reference.md) <br>
- [Video PAS with event-verification reasoning](references/event-verification-reasoning.md) <br>
- [Video PAS reasoning run reference](references/event-verification-reasoning/run-reference.md) <br>
- [CDF NGC Containers](references/ngc-containers.md) <br>
- [CDF Auto-Labeling Pipeline Migration](references/pipeline-migration.md) <br>
- [Migration Playbook](references/pipeline-migration/migration-playbook.md) <br>
- [Nonlinear Video Pipeline Example](references/pipeline-migration/nonlinear-video-pipeline-example.md) <br>
- [Service Reuse Matrix](references/pipeline-migration/service-reuse-matrix.md) <br>
- [Sidecar Contracts](references/pipeline-migration/sidecar-contracts.md) <br>
- [CDF Auto-Labeling Prompt Authoring](references/prompt-authoring.md) <br>
- [Domain Evidence Checklists](references/prompt-authoring/domain-evidence-checklists.md) <br>
- [Prompt Patterns](references/prompt-authoring/prompt-patterns.md) <br>
- [Question-Bank Authoring](references/prompt-authoring/question-bank-authoring.md) <br>
- [CDF Auto-Labeling Scenario Planning](references/scenario-planning.md) <br>
- [Annotation Recommendations](references/scenario-planning/annotation-recommendations.md) <br>
- [Intake And Decisions](references/scenario-planning/intake-and-decisions.md) <br>
- [Pipeline Composition](references/scenario-planning/pipeline-composition.md) <br>
- [Captioning stage](references/stages/captioning.md) <br>
- [Detection and Tracking stage](references/stages/detection-and-tracking.md) <br>
- [Detection And Tracking Patterns](references/stages/detection-tracking-patterns.md) <br>
- [Grounding 2D patterns](references/stages/grounding-2d-patterns.md) <br>
- [Grounding 2D stage](references/stages/grounding-2d.md) <br>
- [Stage configuration guardrails](references/stages/guardrails.md) <br>
- [Person Attribute Search stage](references/stages/person-attribute-search.md) <br>
- [Reasoning stage](references/stages/reasoning.md) <br>
- [Referring Expressions patterns](references/stages/referring-expressions-patterns.md) <br>
- [Referring Expressions stage](references/stages/referring-expressions.md) <br>
- [Super Resolution stage](references/stages/super-resolution.md) <br>
- [Training-export stage](references/stages/training-export.md) <br>
- [Visual QA stage](references/stages/visual-qa.md) <br>
- [CDF Video Data Augmentation Pipeline](references/video-data-augmentation.md) <br>
- [Video Data Augmentation Run Reference](references/video-data-augmentation/run-reference.md) <br>
- [CDF Workflow Runner Debugging](references/workflow-runner-debugging.md) <br>
- [Data Handoff Contract](references/workflow-runner-debugging/data-handoff.md) <br>
- [Workflow Runner Debugging Patterns](references/workflow-runner-debugging/runner-debugging-patterns.md) <br>
- [CDF Workflow Stage Integration](references/workflow-stage-integration.md) <br>
- [Stage And Service Contract](references/workflow-stage-integration/stage-service-contract.md) <br>
- [Validation Checklist](references/workflow-stage-integration/validation-checklist.md) <br>


## Skill Output: <br>
**Output Type(s):** [Shell commands, Configuration instructions, Files] <br>
**Output Format:** [Markdown with inline bash code blocks and YAML cookbook configuration] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [None] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-5-5`) <br>
- Codex (`openai/openai/gpt-6.1-sol`) <br>



## Evaluation Tasks: <br>
4 evaluation tasks (4 positive), 1 attempt per task, each run in its own isolated sandbox pod in the `k8s-sandbox` environment; each task was also attempted without the skill as a baseline. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Is it safe to use? Scored from `security` (100%). <br>
- Correctness: Is the answer correct? Scored from `accuracy` (100%). <br>
- Discoverability: Was the right skill loaded when needed? Scored from `skill_execution` (100%). <br>
- Effectiveness: Did the skill help complete the task? Scored from `goal_accuracy` (50%) + `behavior_check` (50%). <br>
- Efficiency: Did it avoid wasted tool calls and token usage? Scored from `skill_efficiency` (50%) + `token_efficiency` (50%). <br>

Underlying evaluation signals used in this run: <br>
- `security`: Security: unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Skill Execution: whether the expected skill was selected, decoys were avoided, and the workflow executed. <br>
- `skill_efficiency`: Tool Productivity: tool-call productivity (legacy wire id; routing is scored under Discoverability). <br>
- `accuracy`: Accuracy: final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Goal Accuracy: whether the user's goal was achieved. <br>
- `behavior_check`: Behavior Check: whether the expected workflow behavior was followed. <br>
- `token_efficiency`: Token Efficiency: actual uncached prompt plus completion usage (50% of Efficiency). <br>



## Evaluation Results: <br>
> ✅ **Overall verdict: PASS — Recommended for publication**

### Publication Recommendation

Recommended for publication based on the completed evaluation evidence in this report.

### Results at a Glance

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

#### Comparison details

Shared-source comparisons use the same signals and weights on both conditions. They do not replace the full dimension scores above or change the publication verdict.

| Agent | Dimension | Basis | Baseline → With skill (uplift) | Explanation |
| --- | --- | --- | --- | --- |
| claude-code | Discoverability | Dimension comparison | N/A | Discoverability is not applicable to the no-skill baseline; there is no installed skill to discover. |
| claude-code | Efficiency | Token-only comparison | 98.4% → 96.1% (-2.3 points) | Only Token Efficiency is comparable; the full dimension scores use different evaluator sources. |
| codex | Discoverability | Dimension comparison | N/A | Discoverability is not applicable to the no-skill baseline; there is no installed skill to discover. |
| codex | Efficiency | Token-only comparison | 92.0% → 91.3% (-0.7 points) | Only Token Efficiency is comparable; the full dimension scores use different evaluator sources. |

## Skill Version(s): <br>
1.1.0 (source: frontmatter, pyproject.toml, CHANGELOG released 2026-08-15) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
