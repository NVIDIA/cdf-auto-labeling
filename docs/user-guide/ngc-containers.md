# NGC Containers

Every Auto-Labeling stage ships as a prebuilt container image in the
[NGC Catalog](https://catalog.ngc.nvidia.com/search?query=cdf-). Pull those
images instead of running `make build` when you want to run a cookbook
without building the stage images yourself.

## Images

All images live in the public `nvidia` org at `nvcr.io/nvidia/<image>`. The
v1.1.0 release tag is `1.1.0`, and each tag is a multi-arch image for
`linux/amd64` and `linux/arm64`.

| Stage | Image | Catalog page |
| --- | --- | --- |
| Workflow runner (containerized launcher) | `nvcr.io/nvidia/cdf-workflow-runner:1.1.0` | [cdf-workflow-runner](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-workflow-runner) |
| `super_resolution` | `nvcr.io/nvidia/cdf-super-resolution-service:1.1.0` | [cdf-super-resolution-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-super-resolution-service) |
| `detection_and_tracking` (RF-DETR, default) | `nvcr.io/nvidia/cdf-detection-and-tracking-rfdetr-service:1.1.0` | [cdf-detection-and-tracking-rfdetr-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-detection-and-tracking-rfdetr-service) |
| `detection_and_tracking` (SAM3) | `nvcr.io/nvidia/cdf-detection-and-tracking-sam3-service:1.1.0` | [cdf-detection-and-tracking-sam3-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-detection-and-tracking-sam3-service) |
| `referring_expressions` | `nvcr.io/nvidia/cdf-referring-expressions-service:1.1.0` | [cdf-referring-expressions-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-referring-expressions-service) |
| `captioning` | `nvcr.io/nvidia/cdf-captioning-service:1.1.0` | [cdf-captioning-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-captioning-service) |
| `grounding_2d` (default) | `nvcr.io/nvidia/cdf-grounding-2d-service:1.1.0` | [cdf-grounding-2d-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-grounding-2d-service) |
| `grounding_2d` (SAM3) | `nvcr.io/nvidia/cdf-grounding-2d-sam3-service:1.1.0` | [cdf-grounding-2d-sam3-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-grounding-2d-sam3-service) |
| `visual_qa` | `nvcr.io/nvidia/cdf-visual-qa-service:1.1.0` | [cdf-visual-qa-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-visual-qa-service) |
| `reasoning` | `nvcr.io/nvidia/cdf-reasoning-service:1.1.0` | [cdf-reasoning-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-reasoning-service) |
| `training_export` | `nvcr.io/nvidia/cdf-training-export-service:1.1.0` | [cdf-training-export-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-training-export-service) |
| `person_attribute_search` | `nvcr.io/nvidia/cdf-event-and-person-attribute-search-service:1.1.0` | [cdf-event-and-person-attribute-search-service](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cdf-event-and-person-attribute-search-service) |

Check the catalog page for newer tags before you pin a different release.
Pull only the images for the stages your cookbook enables.

## Log In To nvcr.io

These images allow anonymous pulls, so `docker pull` works without logging in.
Log in when you want pulls tied to your NGC account, for example on shared
hosts or CI runners.

1. Create a personal API key in the [NGC web console](https://org.ngc.nvidia.com/setup)
   (**Setup** > **Generate Personal Key**) with the NGC Catalog service enabled.
2. Export the key in your shell. Do not commit it or paste it into a cookbook.

   ```bash
   export NGC_API_KEY=<your-key>
   ```

3. Log in. The username is the literal string `$oauthtoken`, so keep it in
   single quotes:

   ```bash
   echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
   ```

   With Podman, use `podman login` with the same arguments.

`--password-stdin` keeps the key out of your shell history and process list.
Run `docker logout nvcr.io` to remove the stored credential.

## Use Pulled Images With The Workflow Runner

The workflow runner does not pull images. It starts each stage with the bare
image name (for example `cdf-captioning-service`) and expects that image to be
present locally. Pick one of these two approaches.

### Option A: `make pull` (recommended)

`make pull` pulls each image from NGC and tags it with its local name, so every
shipped cookbook works unchanged:

```bash
make pull
```

By default it pulls all 12 images at the current release tag. Pull only the
stages your cookbook enables with `NGC_IMAGES`:

```bash
make pull NGC_IMAGES="cdf-captioning-service cdf-visual-qa-service cdf-reasoning-service cdf-detection-and-tracking-sam3-service"
```

| Variable | Default | Use |
| --- | --- | --- |
| `NGC_IMAGES` | All 12 images in the table above | Space-separated image names to pull |
| `NGC_TAG` | `1.1.0` | Release tag to pull |
| `NGC_REGISTRY` | `nvcr.io/nvidia` | Registry path the images are pulled from |
| `CONTAINER_RUNTIME` | `docker` | Set to `podman` to pull with Podman |

The target stops at the first image that fails to pull. It does not log in,
so run the login step above first if you want authenticated pulls. Once the
tagged images exist, `--container-ensure-images` finds them and skips the
local build.

### Option B: Point stages at the registry references

Pin full references in the cookbook `container.images` block:

```yaml
container:
  images:
    captioning: nvcr.io/nvidia/cdf-captioning-service:1.1.0
    detection_and_tracking: nvcr.io/nvidia/cdf-detection-and-tracking-sam3-service:1.1.0
```

Pull the referenced images first, for example with
`docker pull nvcr.io/nvidia/cdf-captioning-service:1.1.0`. Or override one
stage on the command line with `--captioning-image`,
`--tracking-image`, `--visual-qa-image`, `--reasoning-image`,
`--training-export-image`, `--pas-image`, `--grounding-2d-image`,
`--referring-expressions-image`, or `--sr-image`. Command-line flags take
precedence over the cookbook. Do not combine registry
references with `--container-build-images`, because that flag rebuilds every
stage image from source.

## Verify

Confirm the images are present, then dry-run the cookbook:

```bash
docker image ls 'cdf-*'
make run SCRIPT=workflow-runner:main \
  ARGS='--cookbook-file <cookbook.local.yaml> --container-dry-run'
```

The dry run prints the `docker run` command for every stage. Check that each
command uses the image you expect.

Pulled images do not change the host requirements. GPU stages still need the
NVIDIA driver, the NVIDIA Container Toolkit, and the checkpoints and mounts
described in [Model Provisioning](model-provisioning.md).
