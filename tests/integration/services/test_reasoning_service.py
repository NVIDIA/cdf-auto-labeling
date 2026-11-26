# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Source CLI integration check for reasoning without model configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from service_harness import RunService, entries_payload

pytestmark = pytest.mark.integration


def test_reasoning_without_config_runs_validation_only(
    run_service: RunService,
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "clip.mp4"
    media_path.write_bytes(b"video")
    scene_dir = tmp_path / "scene"
    payload = entries_payload([{"media_path": str(media_path), "data_path": str(scene_dir)}])

    result = run_service("reasoning-service", ["--input", payload])

    result.assert_ok()
    assert result.output.count("DAFT validation passed for") == 2
    assert not list((scene_dir / "task").glob("*.json"))
