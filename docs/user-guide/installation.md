# Installation

Install Auto-Labeling so you can run a cookbook. This is the product
install path for customers and operators.

If you are changing the code, do this install first, then continue with
[Local Development](../developer/local-development.md).

## Requirements

Install only what the selected workflow needs.

| Item | Requirement |
| --- | --- |
| OS | Linux; native Windows execution is outside the supported product path |
| Container runtime | Docker with access to `/var/run/docker.sock` |
| Launcher | GNU Make; Git to obtain the cookbooks and Makefile |
| GPU stages | NVIDIA driver, NVIDIA Container Toolkit, and model checkpoints |
| VLM/LLM stages | Reachable endpoint and matching credentials |
| Remote storage | [MSC configuration](remote-storage.md), consumed inside Linux containers |

Host Python is not needed for container execution (`make run`).
`make build` requires host Python 3.12+ to run `scripts/build.py`; invoking Docker
build commands directly does not. `uv` and a host `.venv` are needed only for
source development. See [Local Development](../developer/local-development.md)
for the optional source setup.

GPU stages need the
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
(or an equivalent GPU runtime) so stage containers can see the GPU.

`ffmpeg` / `ffprobe` on the host is required whenever a video stage runs
directly on the host (the optional source CLI), and to chunk the NGC VSS sample
clips. Stage containers ship their own. Install it with
`apt-get install ffmpeg` on Ubuntu. See the [media policy](#media-policy) for
codec and GPU requirements. SAM3,
SeedVR2, and RF-DETR checkpoints are required only for the stages that use
them. See [Model Provisioning](model-provisioning.md).

## Clone And Pull

```bash
git clone "<repo-url>" cdf-auto-labeling
cd cdf-auto-labeling
make pull
```

`make pull` downloads images; it does not install Python packages. Select only
needed images using `NGC_IMAGES` as described in [NGC Containers](ngc-containers.md).
The updated runner needs the Docker CLI inside its image. Until that image is
published, build it from this checkout after pulling:

```bash
docker buildx build --load -t cdf-workflow-runner \
  -f services/workflow_runner/docker/Dockerfile .
```

Copy tracked cookbooks to `*.local.yaml` before you edit paths. Those
`*.local.yaml` files are gitignored so machine-specific paths and endpoints
do not get committed.

## Verify The Install

Confirm the workflow-runner entrypoint resolves:

```bash
make run ARGS='--help'
```

For a no-GPU service check, follow the
[smoke test](experiment-output-layout.md#no-gpu-smoke-test). After configuring
a local cookbook and staging its inputs, use `--container-dry-run` as shown in
[Getting Started](getting-started.md). This starts the runner container and
prints stage commands without starting annotation-stage containers. It does
not test model inference or endpoint access.

You still need, before [Getting Started](getting-started.md):

1. Checkpoints for the stages you will run —
   [Model Provisioning](model-provisioning.md)
2. A VLM/LLM endpoint and an API key in your shell —
   [VLM and LLM Endpoints](vlm-llm-endpoints.md)
3. Staged NGC traffic/warehouse clips for a real sample run —
   [Samples and Cookbooks](samples-and-cookbooks.md#download-vss-sample-clips)
4. Remote storage config only if media or outputs are not on local disk —
   [Remote Storage](remote-storage.md)
5. Stage images, either built with `make build` or pulled prebuilt from NGC
   with `make pull` — [NGC Containers](ngc-containers.md)

Never put API keys or cloud credentials in cookbook YAML. Export them in the
shell and pass the variable name with `--container-env`. Custom variables must
also be forwarded into the runner; see
[container mounts and environment](operations-workflow-runner.md#container-launcher-mounts).

## Limitations

- `workflow-runner` is a local sequential launcher, not a scheduler.
- `grounding_2d` and `referring_expressions` are image-only.
- Person Attribute Search is an assembly stage: it needs upstream sidecars or
  explicit attribute JSON.
- `reasoning-service` documents `openai-compatible` as its LLM provider surface.
- Secrets belong in the environment or the execution platform, not in tracked
  configs.
- The repo does not publish a qualified performance matrix. Time a short
  representative asset on your cookbook and serving stack before you scale.

### Media Policy

- Supported input video codecs are H.264, VP9, and MPEG-4 Part 2 only.
- H.264 requires the NVIDIA CUVID hardware decoder.
- Generated videos are standardized on VP9 output.
