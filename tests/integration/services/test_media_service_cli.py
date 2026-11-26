# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Service CLI checks for disabled execution and automatic resolution policy."""

from __future__ import annotations

from pathlib import Path

import pytest
from core import read_pipeline_state
from service_harness import RunService, entries_payload, generate_vp9_video

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("project", ["super-resolution-service", "detection-and-tracking-service"])
def test_disabled_service_leaves_inputs_untouched(
    run_service: RunService, tmp_path: Path, project: str
) -> None:
    media_path = tmp_path / "clip.mp4"
    media_path.write_bytes(b"video")
    scene_dir = tmp_path / "scene"
    payload = entries_payload([{"media_path": str(media_path), "data_path": str(scene_dir)}])
    result = run_service(project, ["--disabled", "--input", payload])
    result.assert_ok()
    assert media_path.read_bytes() == b"video"
    assert not scene_dir.exists()


def test_super_resolution_auto_policy_skips_high_res_input(
    run_service: RunService, tmp_path: Path
) -> None:
    media_path = generate_vp9_video(tmp_path / "hires.webm", width=1280, height=720, seconds=0.25)
    scene_dir = tmp_path / "scene"
    payload = entries_payload([{"media_path": str(media_path), "data_path": str(scene_dir)}])
    result = run_service(
        "super-resolution-service",
        [
            "--input",
            payload,
            "--resolution-policy",
            "auto",
            "--min-input-short-side",
            "720",
            "--min-input-long-side",
            "1280",
            "--empty-output-policy",
            "warn",
        ],
    )
    result.assert_ok()
    state = read_pipeline_state(scene_dir)
    assert state.enhanced_media is not None
    assert state.enhanced_media.success is False
    assert state.enhanced_media.output_path is None
    assert "Skipping super-resolution" in result.output
