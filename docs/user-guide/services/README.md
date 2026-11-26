# Services

Auto-Labeling is built from small, single-purpose services. Each
service reads and writes one shared scene format (a **DAFT scene** — the
per-item output directory described in
[Experiment Output Layout](../experiment-output-layout.md)), so services can run
standalone, be chained by the [workflow runner](../operations-workflow-runner.md),
or be orchestrated by an external platform.

Every page below follows the same structure: what the service does, what it
needs before you start it, a copy-pasteable walkthrough, how to confirm it
worked, and where to look when it doesn't.

If this is your first time running Auto-Labeling, start with
[Getting Started](../getting-started.md). Come back here when you need one
stage on its own. If you are adding a service, see
[Adding A New Task Or Service](../../developer/adding-a-task-or-service.md).

## Index

| Service | What it does | Needs a GPU + local checkpoint? | Needs a VLM/LLM endpoint? |
| --- | --- | --- | --- |
| [Super Resolution](super-resolution.md) | Upscales low-resolution video before annotation | Yes (SeedVR2) | No |
| [Detection and Tracking](detection-and-tracking.md) | Finds and tracks objects across a video or image | Yes (RF-DETR or SAM3) | No |
| [Captioning](captioning.md) | Describes what is happening in an image or video | No | Yes (VLM, optional LLM) |
| [Visual QA](visual-qa.md) | Answers a fixed question bank about a scene | No | Yes (VLM, optional LLM) |
| [Reasoning](reasoning.md) | Derives higher-level events and open-ended QA from existing scene data | No | Yes (LLM) |
| [Visual Attribute Search](event-and-person-attribute-search.md) | Assembles person attributes and generates tiered search queries | No | Yes (LLM, optional VLM upstream) |
| [2D Grounding](grounding-2d.md) | Links caption phrases to boxes and masks in an image | Yes (SAM3) | Yes (VLM) |
| [Referring Expressions](referring-expressions.md) | Generates a short phrase that uniquely identifies each detected box | No | Yes (VLM) |
| [Training Export](training-export.md) | Packages completed scenes into a training-ready dataset | No | No |
| [Workflow Runner](../operations-workflow-runner.md) | Compiles a cookbook into an ordered chain of the services above and runs them locally | Depends on selected stages | Depends on selected stages |

## Before running any service for real

Every service can be smoke-tested with no models, GPU, or network access — see
each page's first step. Before a **real** run, make sure you have:

1. Followed [Installation](../installation.md) so `make sync` has completed.
2. Downloaded the checkpoints your chosen services need — see
   [Model Provisioning](../model-provisioning.md).
3. A reachable VLM and/or LLM endpoint — see
   [VLM and LLM Endpoints](../vlm-llm-endpoints.md).
4. A `DataEntry` JSONL manifest pointing at your media — see
   [Experiment Output Layout](../experiment-output-layout.md) for the shape.

## Running one service versus a full workflow

You can invoke any service directly with `make run SCRIPT=<service>:main` —
useful for debugging one stage in isolation. For a real end-to-end pipeline
(for example: detect, then caption, then answer questions, then reason), use
the [workflow runner](../operations-workflow-runner.md) with a
[cookbook](../samples-and-cookbooks.md) instead of chaining services by hand;
it resolves stage order, mounts, and shared scene paths for you.

## Configuration files and CLI overrides

Every service accepts `--config-file settings.yaml` (JSON also works).
For services other than reasoning and PAS, keys match CLI option names, without
`--`; hyphens and underscores are both accepted. Values keep their types:

```yaml
# captioning.local.yaml
input_file: /data/input.jsonl
vlm_endpoint_url: https://inference-api.nvidia.com/v1
vlm_model: replace-with-served-model-name
media_mode: video
single_window: true
max_frames: 16
```

```bash
python -m captioning_service.main \
  --config-file captioning.local.yaml --max-frames 8 --no-single-window
```

These are service arguments, so they work with container entrypoints too; mount
the configuration and referenced files at paths the container can access.
Direct Python execution requires the service's dependencies installed.
Configuration paths have the same meaning as CLI paths: relative paths use the
process working directory. A workflow-runner config holds runner CLI options;
`--cookbook-file` remains the separate interface for pipeline cookbooks.

Precedence is **defaults → configuration file → `--set` → explicit named CLI
flags**. CLI lists replace file lists; repeatable options use YAML/JSON lists.
Boolean flags support `--no-...` to turn off a file setting. Unknown settings,
invalid choices, and missing required arguments fail before service execution.
Credentials remain in environment variables; do not put secrets in configs.

Reasoning and event/person attribute search (PAS) retain their existing task
configuration formats. Override any task field with repeatable `--set KEY=VALUE`:

```bash
python -m reasoning_service.main \
  --input-file input.jsonl --config-file reasoning.local.yaml \
  --set events.enabled=true --set events.max_tokens=4096 \
  --set causal_linkage.max_pairs_auto=3 \
  --llm-endpoint-url https://inference-api.nvidia.com/v1 \
  --llm-model replace-with-served-model-name
```

`--set` also works without a config file. Use dotted field names for nested
settings, JSON for booleans/numbers/lists/objects/null, and plain strings for
text. Existing task schemas validate these overrides; misspelled fields and
invalid values are rejected. For example, enable open QA without YAML:

```bash
python -m reasoning_service.main --input-file input.jsonl \
  --set open_qa.enabled=true \
  --set 'open_qa.questions=["What happened in the scene?"]' \
  --llm-endpoint-url https://inference-api.nvidia.com/v1 \
  --llm-model replace-with-served-model-name
```

In reasoning/PAS config files, put service-level CLI settings in an optional
top-level `cli` mapping, alongside the existing task configuration:

```yaml
cli:
  input_file: /data/input.jsonl
  llm_endpoint_url: https://inference-api.nvidia.com/v1
  llm_model: replace-with-served-model-name
reasoning:
  events:
    enabled: true
```

Reasoning's prompt/bank paths in its task configuration remain relative to the
config file; without a file they use the working directory. CLI overrides of
those task fields follow that same rule. No automatic task enabling occurs:
set the corresponding `enabled` field explicitly.
