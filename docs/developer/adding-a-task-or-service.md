# Adding A New Task Or Service

This page is the map, not the full instructions — the authoritative,
up-to-date steps live in the root [`AGENTS.md`](../../AGENTS.md), which both
human contributors and coding agents follow. Read the relevant section there
before starting; this page just tells you which section to read and where it
fits relative to everything else in `docs/developer/`.

## Before You Start

1. Follow [Local Development](local-development.md) so `make lint-check`,
   `make mypy`, and `make test` pass on a clean tree. Then read
   [`AGENTS.md`](../../AGENTS.md) for the `services -> tasks -> core`
   dependency direction, script/image discovery, and code conventions.
2. Read [Architecture: Services Overview](architecture/services-overview.md)
   and [Architecture: Artifact Contract](architecture/artifact-contract.md) so
   you know where a new stage fits in the stage order and what it's allowed to
   read or write in a scene.
3. If you're adding VLM/LLM behavior, also read
   [Architecture: Model Client Architecture](architecture/model-client-architecture.md).

## Adding A Task Package

Task packages hold reusable annotation behavior and depend only on `core`.
Follow **["Adding a New Task"](../../AGENTS.md#adding-a-new-task)** in
`AGENTS.md`: duplicate `packages/tasks/example_task/`, keep the same
structure and README shape as that template, register it by running
`make sync` (the workspace glob picks it up automatically — no manual
registration step).

## Adding A Service

Services package a task (or several) as a CLI and container. Follow
**["Adding a New Service"](../../AGENTS.md#adding-a-new-service)** in
`AGENTS.md`: duplicate `services/example_service/`, register its entrypoint
under `[project.scripts]` so it's discoverable from `make run`, and register
its image under `[tool.build.images]` so it's discoverable from `make build`.

Once your service exists, add its own step-by-step page under
[`docs/user-guide/services/`](../user-guide/services/README.md) following the
existing pages there (what it does, prerequisites, numbered run steps, verify,
troubleshoot) so operators can find and run it the same way they find every
other service.

### Configuration contract

Use `ServiceInterface.build_parser()` for every service entrypoint. It supplies
`--config-file`, `--set`, and named-flag precedence through the shared
`core.interfaces.config_args` module. Keep the order **defaults → file settings →
`--set` → explicit named flags**, and validate the final configuration with the
service's Pydantic model.

Reuse `read_config()` for file loading and `override_config()` for dotted updates;
the latter uses OmegaConf with replacement semantics. Do not introduce another
service-specific override parser or enable interpolation of prompt strings.
Services with nested task schemas, such as PAS and Reasoning, select their task
section and map named flags to task fields, but use these same shared helpers.
Reuse `args.config_snapshot` during execution instead of reading the file again.
See [Configuration files and CLI overrides](../user-guide/services/README.md#configuration-files-and-cli-overrides)
for the supported file shapes and command examples.

## Bringing Your Own Detector

A detector backend plugs into the existing detection-and-tracking service; it
does not need a new task or service. Subclass `Tracker`, write the canonical
artifacts with `write_tracking_artifacts`, and publish a builder in your own
package under the `cdf.trackers` entry-point group:

```python
# my_detector/tracker.py
from detection_and_tracking import DetectionAndTrackingConfig
from detection_and_tracking.backends.runtime import (
    instances_json_path, objects_json_path, write_tracking_artifacts,
)
from detection_and_tracking.tracker import Tracker, TrackingResult


class MyTracker(Tracker):
    def run(self, media_path, scene_paths, *, scene_ctx) -> TrackingResult:
        frames, instances = ...  # your model; see the field contract below
        write_tracking_artifacts(
            scene_paths=scene_paths, scene_ctx=scene_ctx, frames=frames, instances=instances
        )
        return TrackingResult(
            success=True,
            objects_json=objects_json_path(scene_paths),
            instances_json=instances_json_path(scene_paths),
        )


def build_tracker(logger, config: DetectionAndTrackingConfig) -> Tracker:
    return MyTracker(logger)
```

```toml
# my_detector/pyproject.toml
[project.entry-points."cdf.trackers"]
my-detector = "my_detector.tracker:build_tracker"
```

Install it into the same environment and run
`make run SCRIPT=detection-and-tracking-service:main ARGS="--tracker my-detector --input-file <input.jsonl>"`. No CDF file changes
are needed; an unknown `--tracker` lists the registered kinds. For
`--extract-crops`, write the `instances.json` fields in
[Artifact Contract §1.3](architecture/artifact-contract.md#13-instancesjson-fields-read-by-crop-extraction).
Use the RF-DETR backend (`backends/rfdetr.py`) as a complete reference.

## Related Guidance

- [Local Development](local-development.md) — contributor checks, templates,
  and image registration
- [`AGENTS.md`](../../AGENTS.md) — code conventions, testing, CI/CD, and the
  full command reference (`make lint`, `make mypy`, `make test`, `make check`)
- [`skills/`](../../skills/README.md) — task-shaped agent guidance, including
  [workflow-stage-integration](../../skills/cdf-auto-labeling/references/workflow-stage-integration.md)
  for implementing or reviewing a single new stage or service end to end
- [Package And Service Index](README.md#package-and-service-index) — every
  existing task/service README, for finding a close analog to model yours on
