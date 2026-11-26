# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Reusable helpers and types for the service integration test suite.

This module is importable from both ``conftest.py`` and the test modules because
``tests/integration/services`` is on the pytest ``pythonpath``. Keeping the logic
here lets tests share strongly typed helpers without depending on
conftest module-import semantics.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import run as workspace_run
from core.formats.daft import daft_envelope
from core.media import Vp9VideoWriter
from core.scene import SceneContext, ensure_scene_skeleton

REPO_ROOT = Path(__file__).resolve().parents[3]

# Includes interpreter startup and workspace dependency resolution.
DEFAULT_SERVICE_TIMEOUT_S = 120


@dataclass
class ServiceResult:
    """Outcome of launching a workspace service entrypoint."""

    target: str
    returncode: int
    stdout: str
    stderr: str

    def assert_ok(self) -> None:
        """Fail with captured output when the service exited non-zero."""
        if self.returncode != 0:
            raise AssertionError(
                f"Service `{self.target}` exited with code {self.returncode}.\n"
                f"--- stdout ---\n{self.stdout}\n--- stderr ---\n{self.stderr}"
            )

    @property
    def output(self) -> str:
        """Combined stdout and stderr, useful for log assertions."""
        return f"{self.stdout}\n{self.stderr}"


# Signature: run(project_name, args, *, env=None, timeout=...) -> ServiceResult
RunService = Callable[..., ServiceResult]


def build_service_runner() -> RunService:
    """Build a callable that launches workspace services the way ``make run`` does."""

    # ``run`` (scripts/run.py) is importable because scripts/ is on the pytest pythonpath.
    runnables = {runnable.project_name: runnable for runnable in workspace_run.discover_runnables()}

    def _run(
        project_name: str,
        args: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int = DEFAULT_SERVICE_TIMEOUT_S,
    ) -> ServiceResult:
        try:
            runnable = runnables[project_name]
        except KeyError:
            available = ", ".join(sorted(runnables))
            raise KeyError(
                f"Unknown service `{project_name}`. Available services: {available}."
            ) from None

        command = [
            "uv",
            "run",
            "--package",
            runnable.project_name,
            "python",
            "-c",
            workspace_run.ENTRYPOINT_RUNNER,
            runnable.entrypoint,
            *[str(arg) for arg in args],
        ]
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=proc_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return ServiceResult(
            target=f"{project_name}:{runnable.script_name}",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    return _run


def generate_vp9_video(
    path: Path,
    *,
    seconds: float = 2.0,
    fps: float = 8.0,
    width: int = 256,
    height: int = 144,
) -> Path:
    """Write a small policy-compliant VP9 video fixture via the shared PyAV writer.

    Encoding uses PyAV's bundled libvpx, so it does not require a system ffmpeg — but
    decoding the fixture inside a service still needs ffmpeg on PATH.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(int(seconds * fps), 1)
    with Vp9VideoWriter(path, width=width, height=height, fps=fps, frame_format="bgr24") as writer:
        for index in range(frame_count):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            progress = index / max(frame_count - 1, 1)
            box_x = int(progress * (width - 40))
            frame[height // 2 - 20 : height // 2 + 20, box_x : box_x + 40] = (0, 0, 255)
            writer.write(frame)
    return path


def build_completed_scene(scene_dir: Path, *, media_id: str = "clip") -> Path:
    """Build a completed DAFT scene with one MCQ task item for training-export input."""
    paths = ensure_scene_skeleton(scene_dir)
    (paths.raw_dir / f"{media_id}.mp4").write_bytes(b"video")

    context = SceneContext(media_id=media_id)
    video_payload = daft_envelope("video", context)
    video_payload.update(
        {"format": "mp4", "fps": 30, "duration": 1.0, "height": 720, "width": 1280}
    )
    _write_json(paths.contextual_dir / "video.json", video_payload)

    mcq_payload = daft_envelope("mcq", context, include_scene_id=False)
    mcq_payload["items"] = [
        {
            "video_id": media_id,
            "question": "Which object moves?",
            "options": {"A": "Car", "B": "Bike"},
            "answer": "A",
        }
    ]
    _write_json(paths.task_dir / "mcq.json", mcq_payload)
    return scene_dir


def entries_payload(entries: list[dict[str, Any]]) -> str:
    """Serialize DataEntry records for a service ``--input`` argument."""
    return json.dumps(entries)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
