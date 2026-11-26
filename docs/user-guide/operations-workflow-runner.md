# Operations: Workflow Runner

`workflow-runner` reads a cookbook, resolves paths and stage arguments, then
runs the selected stage containers in order on your machine.

```bash
make run ARGS='--help'
```

## Standard Run Pattern

1. Copy a tracked cookbook to `*.local.yaml`
2. Edit media, output, endpoints, model cache, and checkpoint mounts
3. Run `--container-dry-run`
4. Run the real workflow with `--container-user auto`
5. Inspect the scene outputs and pipeline state

```bash
CONFIG=path/to/cookbook.local.yaml
make run \
  ARGS="--cookbook-file ${CONFIG} --container-dry-run"

export NVIDIA_API_KEY="<your-key>"
make run \
  ARGS="--cookbook-file ${CONFIG} --container-user auto \
        --container-env NVIDIA_API_KEY"
```

`--container-user auto` keeps files writable across stages that may have
different image defaults. Pull or build stage images before running. The
containerized runner executes existing images; automatic source builds are
only supported by the host developer launcher.
`--container-env NVIDIA_API_KEY` forwards the key from your shell. Use
`GEMINI_API_KEY` instead when that is the provider on
[VLM and LLM Endpoints](vlm-llm-endpoints.md).

## Container Launcher Mounts

`make run` uses Docker on Linux and runs the launcher as your host
UID/GID, adding the Docker socket group. It mounts the repository at the same
absolute path and places temporary manifests there, so stage containers can
read them through the host daemon. It does not run Docker-in-Docker or expose
a GPU to the launcher. The stage containers request their own GPUs.

The Docker socket grants control of the host container engine. Run only a
trusted runner image. Override the local image with `RUNNER_IMAGE=<image:tag>`.
The current source image includes the Docker CLI; older runner images may not.

Configs, input manifests, media, checkpoints, prompts, and outputs outside the
repository need identity
mounts into the runner as well as the stage mounts generated from the cookbook:

```bash
make run \
  RUNNER_DOCKER_ARGS='--mount type=bind,src=/data,dst=/data' \
  ARGS='--cookbook-file path/to/cookbook.local.yaml --container-user auto'
```

Create the host mount directories first and use the same absolute paths in the
cookbook. These runner mounts do not replace stage mounts. Mount writable output directories
read-write; input-only directories can use `readonly`. A symlink inside the
repository does not make its external target available automatically.

`make run` does not load `.env`; export variables in your shell.
The launcher forwards `NVIDIA_API_KEY`, `GEMINI_API_KEY`, and
`MULTISTORAGECLIENT_CONFIGURATION` from the host environment. For another
variable, add `--env NAME` to `RUNNER_DOCKER_ARGS`, then `--container-env NAME`
to `ARGS` to forward it to stages. File-based MSC configuration also needs an
identity mount for the configuration file and `MSC_CONFIG` forwarded at both
levels. Never put secret values in arguments.

Users and developers use the same `make run` command. After editing source,
rebuild the affected image before running the cookbook again. See
[Local Development](../developer/local-development.md).

For a single service, the existing selector also runs its container:

```bash
make run SCRIPT=captioning-service:main ARGS='--help'
```

The image comes from the service registration and uses the same default backend
as the workflow runner. Use `RUNNER_DOCKER_ARGS` for additional mounts or GPU
access (`--gpus all`) when running a service directly. Workflow cookbooks already
specify stage mounts and GPU access. No host Python installation is involved.

## Cookbook Shape

Most shipped cookbooks follow this shape:

```yaml
pipeline: video | image
workflow:
  nodes:
    <node_id>:
      stage: <stage_name>
      needs: [<upstream_node>]
      args: [--flag, value]
runtime:
  model_cache_path: <path>
  gpu_ids: all
container:
  user: auto
  images: {}
  env: []
  mounts: []
data:
  - id: <optional-scene-id>
    inputs:
      media_path: <path-or-uri>
    output:
      out_dir: <output-root>
endpoints:
  vlm: {url: ..., model: ...}
  llm: {url: ..., model: ...}
```

Copy tracked configs to `*.local.yaml` before editing machine-specific paths.
Keep `container.env` as variable names, not secret values. For the multiview
PAS flow, keep `media_path` as a file so the runner does not expand a directory
into one scene per image.

Which cookbook to copy: [Samples and Cookbooks](samples-and-cookbooks.md).

## Useful Flags

| Flag | When to use it |
| --- | --- |
| `--cookbook-file` | Load a scenario cookbook |
| `--stages ...` | Enable only selected stages |
| `--container-dry-run` | Print the stage plan without execution |
| `--container-user auto` | Run stage containers as the invoking user |
| `--container-env NAME` | Pass a host env var name through to every stage |
| `--container-mount HOST[:CONTAINER[:ro\|rw]]` | Add a bind mount to every stage |
| `--container-ensure-images` | Host developer launcher: build only missing enabled stage images |
| `--container-build-images` | Host developer launcher: rebuild every enabled stage image |
| `--container-network` | Override the default host network behavior |
| `--dev-data-root PATH` | Copy the source scene before writing, so samples are not mutated |
| `--stage-arg STAGE=ARG` | Add one extra flag to a single stage for this run |
| `--policy warn` | Continue after a failed stage so you can inspect a partial scene |

Common forwarded model options include `--model-cache-path`, `--gpu-ids`,
`--vlm-endpoint-url`, `--llm-endpoint-url`, `--question-bank-file`,
`--reasoning-config-file`, `--pas-config-file`, and
`--training-export-format` / `--training-export-dir`.

Typical env vars to pass with `--container-env`: `NVIDIA_API_KEY` or
`GEMINI_API_KEY` for endpoints, and `MSC_CONFIG` or
`MULTISTORAGECLIENT_CONFIGURATION` for remote paths.

`--dev-data-root` copies each source scene before a stage writes to it. Use it
when you want to keep an existing grounding `out_dir` unchanged while running
the referring-only config. See
[Getting Started](getting-started.md#path-d--image-spatial-grounding).

## Local Versus Remote Paths

- Local `media_path` and `data_path` values are mounted into every stage
  container.
- URI-like values such as `s3://...` are left unchanged and require
  [Remote Storage](remote-storage.md) configuration inside every stage
  container.

## Stage Images

Prebuilt images for every stage are published on NGC. Run `make pull` to pull
them and tag them with the local names the runner uses. Details and per-stage
options: [NGC Containers](ngc-containers.md).

For source builds, `make build` uses host Python 3.12+ but does not require
a full workspace sync. Build a registered image from the repository root:

```bash
make build IMAGE=captioning-service:main
```

Registered names:

- `captioning-service:main`
- `detection-and-tracking-service:rfdetr`
- `detection-and-tracking-service:sam3`
- `event-and-person-attribute-search-service:build`
- `grounding-2d-service:main`
- `grounding-2d-service:sam3`
- `reasoning-service:build`
- `referring-expressions-service:main`
- `super-resolution-service:build`
- `training-export-service:build`
- `visual-qa-service:build`
- `workflow-runner:workflow-runner`

GPU images need a compatible NVIDIA driver and container GPU runtime. Mount
model checkpoints read-only when possible. How images are registered in
package metadata:
[Local Development](../developer/local-development.md#image-registration).

## Training Export

The training export stage can be driven from the workflow runner:

```bash
make run \
  ARGS='--input-file payloads/simple.jsonl \
        --training-export-format tao-vl-reason-v1.0 \
        --training-export-dir output/training'
```

Cookbooks can also configure `training_export:` as a terminal stage.

## Scene Logging

For local non-dry runs, the runner appends lightweight execution records to
`<data_path>/logs/workflow_runner.jsonl`. Use that together with
`sidecars/pipeline_state.json` when diagnosing stage order, outputs, or
container return codes.
