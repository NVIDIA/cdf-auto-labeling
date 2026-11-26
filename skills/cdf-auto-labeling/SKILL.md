---
name: cdf-auto-labeling
description: >-
  Use when a user needs to get started with CDF Auto-Labeling, plan a
  scenario, run or debug a shipped cookbook, author prompts or cookbooks,
  migrate a pipeline, configure a stage, or pull the prebuilt stage containers
  from NGC (nvcr.io). Confirm critical inputs (data
  path, output path, endpoints) and ask when any are missing. This is a
  router: read the matching reference instead of inventing a workflow.
license: Apache-2.0
owner: NVIDIA
service: cosmos-data-factory
version: 1.1.0
reviewed: 2026-09-14
author: "NVIDIA <opensource@nvidia.com>"
metadata:
  author: "NVIDIA <opensource@nvidia.com>"
  tags: [getting-started, onboarding, new-domain, quickstart, new-use-case]
---

# CDF Auto-Labeling

Use this skill when a user wants to kick off CDF Auto-Labeling on their
own data, domain, or use case, or when the request matches a shipped cookbook,
stage, authoring, or migration task. This is a router: sequence the specialized
references instead of duplicating their detail.

## Routing (Read First)

| Request looks like | Read |
| --- | --- |
| New user, clean checkout, first validated run, "how do I get started" | This file, then the matching reference below |
| Choose annotation targets / stage subset for a domain | [`references/scenario-planning.md`](references/scenario-planning.md) |
| Create, review, or adapt a cookbook | [`references/cookbook-authoring.md`](references/cookbook-authoring.md) |
| Write or adapt VLM/LLM prompts or question banks | [`references/prompt-authoring.md`](references/prompt-authoring.md) |
| Migrate an existing annotation repo into this one | [`references/pipeline-migration.md`](references/pipeline-migration.md) |
| Run the video data augmentation cookbook | [`references/video-data-augmentation.md`](references/video-data-augmentation.md) |
| Run or choose an EPAS / PAS cookbook | [`references/event-and-person-attribute-search.md`](references/event-and-person-attribute-search.md) |
| Run event-verification reasoning | [`references/event-verification-reasoning.md`](references/event-verification-reasoning.md) |
| Debug an already-integrated workflow | [`references/workflow-runner-debugging.md`](references/workflow-runner-debugging.md) |
| Pull prebuilt stage images from NGC, log in to `nvcr.io`, or fix a missing `cdf-*` image | [`references/ngc-containers.md`](references/ngc-containers.md) |
| Implement or review a new stage or Dockerized service | [`references/workflow-stage-integration.md`](references/workflow-stage-integration.md) |
| Configure or debug one production stage | The matching file under [`references/stages/`](references/stages/) |

Stage references: [super-resolution](references/stages/super-resolution.md),
[detection-and-tracking](references/stages/detection-and-tracking.md),
[captioning](references/stages/captioning.md),
[visual-qa](references/stages/visual-qa.md),
[reasoning](references/stages/reasoning.md),
[person-attribute-search](references/stages/person-attribute-search.md),
[grounding-2d](references/stages/grounding-2d.md),
[referring-expressions](references/stages/referring-expressions.md),
[training-export](references/stages/training-export.md).

## Instructions

1. Confirm the critical run inputs with the user before doing anything else, and
   ask a concise question whenever one is missing or ambiguous - never guess or
   silently invent a default. Confirm only inputs required by the selected stages: input data path, output path,
   VLM/LLM endpoint URLs and model names, model cache path, GPU ids, and (for
   reasoning-capable models) the `max_tokens` cap. Restate the confirmed values
   back to the user before the first execution. Ask once for missing required
   inputs and pause dependent work until supplied; if unavailable, report the
   blocker rather than repeatedly asking or inventing values.
2. Read [Container execution](#container-execution) for host requirements,
   image preparation, mounts, and environment forwarding. Verify the environment:
   repository cloned, `make` targets available, the
   required model cache exists, required endpoints are reachable, and a GPU is
   available only when the selected stages or video decoder require one.
   If a required prerequisite is unavailable, report it and stop the run until
   resolved; do not silently continue with a degraded environment.
   If the stage images are not present locally, offer to pull the prebuilt
   images from NGC with `make pull` instead of building them. Use
   [ngc-containers](references/ngc-containers.md).
3. Run a shipped example first to confirm the stack works end to end before
   customizing. Pick the closest operator pipeline - video data augmentation,
   event-and-person-attribute-search, or event-verification-reasoning - and
   run a configured local copy of its cookbook. Use the matching operator reference.
4. Plan the target scenario: define modality, domain, intended consumer, and
   required annotations, and get a minimal stage subset. Use
   [scenario-planning](references/scenario-planning.md).
5. Adapt the closest shipped cookbook to the new domain rather than authoring
   from scratch. Use [cookbook-authoring](references/cookbook-authoring.md).
6. Author the domain prompts and question banks. Use
   [prompt-authoring](references/prompt-authoring.md).
7. Configure the per-stage settings for the domain (detector classes or SAM3
   prompts, endpoints, windowing, `max_tokens`). Use the relevant stage
   reference, starting with
   [detection-and-tracking](references/stages/detection-and-tracking.md).
8. Follow [Container execution](#container-execution) to dry-run, execute, and
   validate. For failure diagnosis, use
   [workflow-runner-debugging](references/workflow-runner-debugging.md).

Adopting an existing external annotation or dataset-generation repository into
CDF instead of starting from a shipped cookbook is a migration task; use
[pipeline-migration](references/pipeline-migration.md) for that path.

## Container execution

`make run` launches Docker containers; no host Python or `.venv` is needed.
A dry-run starts the runner container, but no annotation-stage containers, and
does not verify inference. Pull or build images before running; automatic build
flags belong to the optional host source CLI. `make build` needs host Python;
direct Docker builds do not. For external paths, GPU access for direct service
runs, and environment forwarding, follow the
[launcher guide](../../docs/user-guide/operations-workflow-runner.md#container-launcher-mounts).
Use a configured `*.local.yaml` copy of a shipped cookbook. Never commit secrets
or machine-specific home paths; pass credential names through the environment.

```bash
CONFIG=path/to/cookbook.local.yaml
make run ARGS="--cookbook-file ${CONFIG} --container-dry-run"
```

Inspect stage order, inputs, output paths, mounts, and endpoints. If the dry-run
fails, correct the identified cause and retry at most three times; stop and
report any unresolved blocker. Once preflight passes and execution is authorized,
run the same command without `--container-dry-run`, then check the expected
artifacts. A dry-run alone is never evidence of successful inference.

## Examples

New user, new domain: "I cloned the repo and have my own warehouse-safety video.
How do I produce auto-labels for my domain?"

Guided path:

- Confirm the required environment, then use [Container execution](#container-execution)
  to validate a configured local copy of the closest shipped cookbook.

- Plan the domain ([scenario-planning](references/scenario-planning.md)) -> subset
  `detection_and_tracking -> captioning -> visual_qa -> reasoning -> training_export`
  (add `grounding_2d` for caption→boxes or `referring_expressions` for boxes→phrases;
  use [grounding-2d](references/stages/grounding-2d.md) /
  [referring-expressions](references/stages/referring-expressions.md)).
- Copy the closest cookbook to `cookbooks/warehouse_safety/configs/pipeline.local.yaml`
  and adapt inputs, detector classes/SAM3 prompts, prompts, and question banks.
- Follow [Container execution](#container-execution) for the adapted cookbook.

## Guardrails

- Do not guess or fabricate the critical inputs enumerated in step 1; if any is
  missing or ambiguous, ask the user and confirm before executing.
- Do not customize a cookbook before a shipped example runs clean; a broken base
  makes domain debugging ambiguous.
- Keep the first custom pipeline minimal - only the stages needed for the
  requested annotations - and expand later.
- Verify that every selected stage's service package and image exist in the
  current branch before promising an end-to-end run.
- Do not put secrets, tokens, or absolute home paths in committed cookbooks; use
  placeholders such as `<model-cache>` and env vars for endpoint keys.
- For reasoning-capable models (for example Gemini 3 Flash), raise `max_tokens`
  on the `visual_qa` and `reasoning` LLM substages to avoid the thinking-token
  tax; keep the default cap for non-reasoning models.
- Do not rely on non-CDF pipelines, commands, or file locations. A first run
  must be reproducible through `workflow-runner:main` inside this repo.
