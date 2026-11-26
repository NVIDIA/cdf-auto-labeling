# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Source CLI integration check for the workflow container plan."""

from __future__ import annotations

from pathlib import Path

import pytest
from service_harness import RunService, entries_payload

pytestmark = pytest.mark.integration


def test_workflow_runner_dry_run_plans_video_pipeline(
    run_service: RunService,
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "clip.mp4"
    media_path.write_bytes(b"video")
    scene_dir = tmp_path / "scene"
    payload = entries_payload([{"media_path": str(media_path), "data_path": str(scene_dir)}])

    result = run_service(
        "workflow-runner",
        [
            "--input",
            payload,
            "--pipeline",
            "video",
            "--no-expand-input-dirs",
            "--container-dry-run",
        ],
    )

    result.assert_ok()
    plans = [line for line in result.output.splitlines() if "Running container node" in line]
    assert plans
    assert all("docker run" in line for line in plans)
    assert any("(stage captioning)" in line for line in plans)
    assert not list(scene_dir.rglob("video_captions.json"))
