# Service CLI integration tests

These tests launch real service entrypoints from the source workspace through
`uv run --package <project> python -c <entrypoint-runner>`, matching the launcher
used by `make run`. They verify imports, argument handling, and deterministic
service behavior without model endpoints, credentials, Docker, or GPUs.

```bash
make test-integration
uv run pytest -m integration tests/integration/services -k training_export
```

The `integration` marker excludes these subprocess tests from the default unit
run. FFmpeg and ffprobe must be on PATH for the super-resolution policy test;
missing prerequisites fail rather than silently skip coverage.

Coverage includes disabled media services, automatic super-resolution skipping,
workflow dry-run planning, reasoning validation without configuration, scene
initialization by the example service, and Cosmos training export.

The resolution test always generates its own tiny 1280×720 VP9 clip so that a
sample-media environment override cannot change the behavior under test.

`service_harness.py` holds the subprocess launcher, VP9 fixture generator, and
completed-scene builder. `conftest.py` exposes shared fixtures. Assertions inspect
service outputs, pipeline state, or artifacts as appropriate. Real model inference
and multi-container workflows belong in `tests/e2e`.
