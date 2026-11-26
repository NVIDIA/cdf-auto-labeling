# Experiment Output Layout

Auto-Labeling writes one **scene** per input: a directory with `raw/`, `contextual/`,
`task/`, and `sidecars/`. Services share that directory instead of calling each
other. Two ways to produce it:

- **Cookbook run (recommended).** Copy a tracked cookbook to `*.local.yaml`,
  set `data[*].output.out_dir`, and run the
  [workflow runner](operations-workflow-runner.md). That is the product path.
  See [Getting Started](getting-started.md).
- **Manual experiment.** Invoke one service yourself with
  `make run SCRIPT=<service>:main`. Use this to debug a single stage or to
  learn the scene contract without compiling a cookbook.

The rest of this page is the directory both paths should use.

## How to run a manual experiment

A manual experiment is a one-service run against a `DataEntry` JSONL file you
create. The service processes it directly; no workflow stages are orchestrated.

1. Create the experiment tree and stage source media:

   ```bash
   EXPERIMENT=/path/to/my-experiment
   mkdir -p "$EXPERIMENT"/{source,logs,data/clip-001}
   cp /path/to/clip.mp4 "$EXPERIMENT/source/clip-001.mp4"
   ```

2. Write `$EXPERIMENT/input.jsonl`. Each line is one `DataEntry`. `media_path`
   is the source file; `data_path` is the scene directory that service will
   write:

   ```json
   {
     "id": "clip-001",
     "media_path": "/path/to/my-experiment/source/clip-001.mp4",
     "data_path": "/path/to/my-experiment/data/clip-001"
   }
   ```

   In the file, keep that object on one JSONL line.

3. Run one service. Captioning is a typical first example once a
   [VLM endpoint](vlm-llm-endpoints.md) is reachable:

   ```bash
   make run SCRIPT=captioning-service:main \
     RUNNER_DOCKER_ARGS="--mount type=bind,src=$EXPERIMENT,dst=$EXPERIMENT" \
     ARGS="--input-file '$EXPERIMENT/input.jsonl'"
   ```

   Use `make run SCRIPT=<service>:main ARGS='--help'` for that service's
   flags. Direct GPU service runs also need `RUNNER_DOCKER_ARGS` with
   `--gpus all` and checkpoint mounts; see
   [container mounts](operations-workflow-runner.md#container-launcher-mounts).
   Provision checkpoints using
   [Model Provisioning](model-provisioning.md).

4. Confirm the scene: `$EXPERIMENT/data/clip-001/sidecars/` should contain
   `pipeline_state.json` plus that stage's artifacts.

To chain stages by hand, keep the same `data_path` and feed the next service
the same JSONL. Prefer a cookbook once you are running more than one stage.

### No-GPU smoke test

Run this from the repository root after [Installation](installation.md), with
the runner and RF-DETR service images available. `make run` uses Docker; Python
and media tools run inside the images. This uses the checked-in MPEG-4 Part 2
clip and the `stub` tracker, so no GPU, checkpoints, endpoint, or host media
tools are needed:

```bash
EXPERIMENT="$PWD/output/smoke"
mkdir -p "$EXPERIMENT"/{source,data/clip-001}
cp data/video_mpeg4.mp4 "$EXPERIMENT/source/clip-001.mp4"
echo '{"id":"clip-001","media_path":"'"$EXPERIMENT"'/source/clip-001.mp4","data_path":"'"$EXPERIMENT"'/data/clip-001"}' \
  > "$EXPERIMENT/input.jsonl"
make run SCRIPT=detection-and-tracking-service:main \
  ARGS="--input-file '$EXPERIMENT/input.jsonl' --tracker stub"
```

The scene gets `contextual/objects.json`, `contextual/instances.json`, and
`sidecars/pipeline_state.json`, and the log includes `DAFT validation passed`.
The stub produces empty detections; this checks service plumbing, not model accuracy.

### VLM stages against a local endpoint

VLM-backed stages call an OpenAI-compatible endpoint for inference. The client
can run without a GPU for images or CPU-decodable video such as the smoke clip
above; H.264 decoding still requires a GPU. A local model server may also need
a GPU. For a local server (vLLM, NIM, ...):

- `NVIDIA_API_KEY` is optional; when unset the client sends `EMPTY`, which
  unauthenticated local servers can accept. Authenticated servers need a valid key.
- One served model can act as both VLM and LLM: `--llm-endpoint-url` and
  `--llm-model` default to the VLM values where the service supports them.
- If the server rejects video input, pass `--media-mode frames`. In the default
  `auto` mode the service attempts a frames request and logs the video error.

```bash
VLM_MODEL="replace-with-served-model-name"
QUESTION_BANK="$PWD/cookbooks/visual_attribute_search/question_bank.anomaly_tags.json"
make run SCRIPT=visual-qa-service:main ARGS="--input-file '$EXPERIMENT/input.jsonl' \
  --generation-mode window-direct-vlm --question-bank-file '$QUESTION_BANK' \
  --vlm-endpoint-url http://localhost:8000/v1 --vlm-model '$VLM_MODEL' \
  --single-window"
```

This reuses the repository-local smoke experiment. Set `VLM_MODEL` to the served
model name. `QUESTION_BANK` uses the existing sample bank
[`cookbooks/visual_attribute_search/question_bank.anomaly_tags.json`](../../cookbooks/visual_attribute_search/question_bank.anomaly_tags.json)
from the repository root. External experiment or question-bank paths also need
[identity mounts](operations-workflow-runner.md#container-launcher-mounts).

For per-track questions, run detection with `--extract-crops` first, then add
`--track-crops-sidecar detection_and_tracking/tracks.json` to visual QA on the
same `data_path`.

Per-service walkthroughs: [Services](services/README.md).

## Directory layout

In the manual layout below, `data/<entry-id>` is the scene passed as
`DataEntry.data_path`. Folders mean:

- `raw/` — media the pipeline is analyzing
- `contextual/` — scene-level objects, tracks, events, and similar metadata
- `task/` — questions, captions, and other task JSON
- `sidecars/` — handoff files: a copy of the original media (`raw.<ext>`),
  the current media for the next stage (`active.<ext>`),
  `pipeline_state.json`, and per-stage extras

```text
<experiment-root>/
  input.jsonl
  source/
    <entry-id>.<ext>
  logs/
    <stage-or-service>.log
  data/
    <entry-id>/
      raw/
      contextual/
      task/
      sidecars/
        raw.<ext>
        active.<ext>
        pipeline_state.json
        logs/
          <task>.log
        <task-artifacts>
```

For a cookbook entry pointing to one file, `out_dir` is the scene directory
itself. When a media directory is expanded, each scene is placed at
`out_dir/<media-filename>` (including its extension). The runner does not add
the manual layout's `data/<entry-id>` wrapper. In either case, `media_path`
must point at real media.

## Rules

- `input.jsonl` is the exact input used for the run.
- `source/` contains the staged source media used by that input.
- `logs/` contains outer service or container logs.
- In the manual layout, `data/<entry-id>` is the value of `DataEntry.data_path`.
- `sidecars/raw.<ext>` preserves the original media once.
- `sidecars/active.<ext>` is the current media handoff for the next stage.

Services should depend on `media_path`, `data_path`, and the scene handoff
inside `sidecars/`, not on the outer experiment-root name. File-level
ownership is in the
[Artifact Contract](../developer/architecture/artifact-contract.md).
