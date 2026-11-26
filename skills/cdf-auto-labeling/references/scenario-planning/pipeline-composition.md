# Pipeline Composition

The CDF runner composes supported stages into a pipeline. The agent selects a
subset of the canonical stages; the runner builds and executes Docker commands.
There is no single fixed pipeline: each cookbook picks the stages it needs, run
in canonical order for `stages:` or dependency order for `workflow.nodes`.

- [Supported Stage Names](#supported-stage-names)
- [Common Pipelines](#common-pipelines)
- [Stage Selection Rules](#stage-selection-rules)
- [Data Flow Contract](#data-flow-contract)
- [Custom Pipeline Compatibility Checks](#custom-pipeline-compatibility-checks)
- [Dry-Run First](#dry-run-first)

## Supported Stage Names

Use the [runner stage model](../cookbook-authoring/cookbook-schema.md#runner-stage-model)
for canonical stage order and defaults. Plain `stages:` uses that order;
`workflow.nodes` uses dependency order. Verify the current checkout before execution.

- Caption → boxes: `captioning` → `grounding_2d` (image-only).
- Boxes → phrases: `detection_and_tracking` → `referring_expressions`, or
  `referring_expressions` alone with existing `contextual/objects.json`.
- PAS consumes explicit attribute JSON or upstream attribute sidecars. Tracking
  alone does not produce that evidence. Attribute-only and multi-view image
  cookbooks do not require tracking; see the
  [PAS cookbook matrix](../event-and-person-attribute-search/run-reference.md#cookbook-matrix).
- The retired `daft_export` stage is replaced by per-task DAFT output and
  `reasoning`; dataset aggregation belongs to `training_export`.

## Common Pipelines

Image caption to training export:

```yaml
stages:
  - captioning
  - reasoning
  - training_export
```

Image VQA to training export, minimal when `visual_qa` does not require
`captioning` artifacts:

```yaml
stages:
  - visual_qa
  - reasoning
  - training_export
```

Add `captioning` before `visual_qa` only when the VQA flow explicitly consumes
caption artifacts; otherwise `visual_qa` can feed `reasoning` directly.

Video captions to training export:

```yaml
stages:
  - captioning
  - reasoning
  - training_export
```

Tracked video auto-labeling:

```yaml
stages:
  - detection_and_tracking
  - captioning
  - visual_qa
  - reasoning
  - training_export
```

Visual Attribute Search over video needs explicit attribute-producing nodes.
Use the shipped `pipeline_video_epas.yaml` with its captioning and per-track QA
settings; the stage subset is:

```yaml
stages:
  - detection_and_tracking
  - captioning
  - visual_qa
  - person_attribute_search
```

Image 2D grounding (caption → expressions → SAM3 boxes):

```yaml
stages:
  - captioning
  - grounding_2d
```

Referring expressions (boxes → phrases):

```yaml
stages:
  - detection_and_tracking
  - referring_expressions
```

Low-resolution video auto-labeling:

```yaml
stages:
  - super_resolution
  - detection_and_tracking
  - captioning
  - visual_qa
  - reasoning
  - training_export
```

Mixed-resolution video auto-labeling:

```yaml
stages:
  - super_resolution
  - detection_and_tracking
  - captioning
  - visual_qa
  - reasoning
  - training_export

stage_args:
  super_resolution:
    - --resolution-policy
    - auto
    - --min-input-short-side
    - "720"
    - --min-input-long-side
    - "1280"
```

Additional shipped example cookbooks include `event_verification_reasoning`
(evidence-first `reasoning` verdicts) and `video_data_augmentation`.

## Stage Selection Rules

- Use `super_resolution` with `--resolution-policy auto` for mixed-resolution
  video datasets; only use unconditional SR when every input is known to need
  enhancement.
- Choose SR output resolution and window size based on hardware. Validate the
  real container on representative clips before a full run because SeedVR2 3B at
  720p can exceed A40 memory.
- Use `detection_and_tracking` when labels need object IDs, trajectories,
  overlays, masks, counts, or object-level grounding.
- Use `captioning` for image/video evidence prose and VLM-derived visual
  descriptions.
- Use `visual_qa` when a question bank should produce reusable visual evidence.
- Use `reasoning` when outputs should be written into DAFT `task/`/contextual
  artifacts or need evidence-first verdicts.
- Use `training_export` when per-scene outputs should be aggregated into a
  training/export dataset.
- Use `person_attribute_search` after its attribute evidence producers, or with
  explicit attribute JSON. Choose the matching PAS cookbook contract.

## Data Flow Contract

Every custom linear pipeline must preserve:

```text
DataEntry.media_path       effective input after prepare_input
DataEntry.data_path        shared scene directory
sidecars/raw.*             preserved original media
sidecars/active.*          current media handoff
sidecars/pipeline_state.json
contextual/
task/
sidecars/logs/
```

Media-transforming stages update active media only after verifying the output
artifact exists. Annotation-only stages should leave active media unchanged.

## Custom Pipeline Compatibility Checks

Before proposing a custom combination, check:

- Does each stage consume outputs produced by earlier stages or by the original
  scene state?
- Does any stage require active media from SR or tracking overlays?
- Does the selected captioning `input_source` match the intended evidence
  source: original, enhanced, tracking, or auto?
- Are prompt files and question banks mounted read-only through cookbook config
  or runner stage args?
- Are model cache and output scene directories mounted with write access where
  needed?
- Does the generated dry-run command include every intended image, build target,
  mount, endpoint, GPU, and stage arg?

## Dry-Run First

Follow the shared [Container execution](../../SKILL.md#container-execution)
procedure and guardrails. Confirm the planned stage order and data-flow assumptions
before executing.
