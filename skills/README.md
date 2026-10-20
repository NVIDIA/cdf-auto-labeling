# Skills

This directory holds the repository-local `cdf-auto-labeling` agent skill for
working in Auto-Labeling. The skill is a router: `SKILL.md` sequences
the task, and the matching page under `cdf-auto-labeling/references/` has the
detail.

These are not user-facing product docs. For that, see the
[user guide](../docs/user-guide/README.md) (operators) or
[developer docs](../docs/developer/README.md) (contributors).

`.claude/skills`, `.agents/skills`, and `.codex/skills` are symlinks to this
directory so local agents load the same pack.

## Pack

| Skill | Use when |
| --- | --- |
| [`cdf-auto-labeling`](cdf-auto-labeling/SKILL.md) | Getting started, planning a scenario, running or debugging a shipped cookbook, authoring prompts or cookbooks, migrating a pipeline, or configuring a stage |

## References

| Reference | Use when |
| --- | --- |
| [scenario-planning](cdf-auto-labeling/references/scenario-planning.md) | Choosing annotation targets and a stage subset for a domain/modality |
| [pipeline-migration](cdf-auto-labeling/references/pipeline-migration.md) | Planning how to migrate an existing annotation/dataset-generation repo |
| [video-data-augmentation](cdf-auto-labeling/references/video-data-augmentation.md) | Running the full video data augmentation cookbook |
| [event-and-person-attribute-search](cdf-auto-labeling/references/event-and-person-attribute-search.md) | Choosing, dry-running, or validating one of the four EPAS/PAS cookbooks |
| [event-verification-reasoning](cdf-auto-labeling/references/event-verification-reasoning.md) | Operating the video PAS + event-verification reasoning cookbook |
| [workflow-runner-debugging](cdf-auto-labeling/references/workflow-runner-debugging.md) | Debugging an already-integrated workflow |
| [ngc-containers](cdf-auto-labeling/references/ngc-containers.md) | Pulling prebuilt stage images from NGC and logging in to `nvcr.io` |
| [cookbook-authoring](cdf-auto-labeling/references/cookbook-authoring.md) | Creating, reviewing, or adapting a cookbook |
| [prompt-authoring](cdf-auto-labeling/references/prompt-authoring.md) | Writing or adapting VLM/LLM prompts |
| [workflow-stage-integration](cdf-auto-labeling/references/workflow-stage-integration.md) | Implementing or reviewing a new stage or Dockerized service |

One reference per production stage, for configuring or debugging that stage
specifically (not for running or authoring a whole cookbook):

| Reference | Stage |
| --- | --- |
| [guardrails](cdf-auto-labeling/references/stages/guardrails.md) | Shared stage configuration rules |
| [super-resolution](cdf-auto-labeling/references/stages/super-resolution.md) | Super resolution |
| [detection-and-tracking](cdf-auto-labeling/references/stages/detection-and-tracking.md) | Detection and tracking |
| [captioning](cdf-auto-labeling/references/stages/captioning.md) | Captioning |
| [visual-qa](cdf-auto-labeling/references/stages/visual-qa.md) | Visual QA |
| [reasoning](cdf-auto-labeling/references/stages/reasoning.md) | Reasoning |
| [person-attribute-search](cdf-auto-labeling/references/stages/person-attribute-search.md) | Person Attribute Search |
| [grounding-2d](cdf-auto-labeling/references/stages/grounding-2d.md) | 2D grounding |
| [referring-expressions](cdf-auto-labeling/references/stages/referring-expressions.md) | Referring expressions |
| [training-export](cdf-auto-labeling/references/stages/training-export.md) | Training export |
