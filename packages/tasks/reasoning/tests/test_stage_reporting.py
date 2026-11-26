# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from core import DataEntry
from core.models import read_pipeline_state, update_annotation_export_state
from reasoning.config import DaftExportConfig, EventsConfig, MstedConfig
from reasoning.paths import ensure_scene_skeleton
from reasoning.task import ReasoningTask, _owned_outputs, _report_unproduced


def test_all_enabled_stages_produced_is_quiet(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        _report_unproduced(["events", "open_qa"], {"events", "open_qa"}, logger=logging.getLogger())
    assert not caplog.records


def test_partial_output_is_a_warning_naming_the_missing_stages(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        _report_unproduced(["events", "open_qa"], {"events"}, logger=logging.getLogger())
    assert "1 of 2 enabled stages wrote nothing: open_qa" in caplog.text


def test_no_output_from_any_enabled_stage_fails() -> None:
    with pytest.raises(RuntimeError, match="every enabled stage was skipped"):
        _report_unproduced(["events", "open_qa"], set(), logger=logging.getLogger())


def test_nothing_enabled_is_not_a_failure() -> None:
    _report_unproduced([], set(), logger=logging.getLogger())


def test_only_enabled_stages_are_recorded(tmp_path: Path) -> None:
    paths = ensure_scene_skeleton(tmp_path / "scene")
    cfg = DaftExportConfig(events=EventsConfig(enabled=True), msted=MstedConfig(enabled=False))
    owned = _owned_outputs(paths, cfg=cfg)
    assert set(owned) == {"events"}
    assert _owned_outputs(paths, cfg=None) == {}


def test_image_temporal_stage_is_not_recorded_as_failed(tmp_path: Path) -> None:

    media = tmp_path / "frame.jpg"
    media.touch()
    scene = tmp_path / "scene"
    ReasoningTask(config=DaftExportConfig(events=EventsConfig(enabled=True))).run(
        DataEntry(media_path=str(media), data_path=str(scene))
    )
    export = read_pipeline_state(scene).annotation_export
    assert export is not None
    assert export.emitters == []


def test_disabled_reasoning_preserves_visual_qa_output(tmp_path: Path) -> None:

    media = tmp_path / "frame.jpg"
    media.touch()
    scene = tmp_path / "scene"
    paths = ensure_scene_skeleton(scene)
    paths.task_open_qa.write_text("{}")
    update_annotation_export_state(scene, emitter_artifacts={"open_qa": paths.task_open_qa})
    ReasoningTask().run(DataEntry(media_path=str(media), data_path=str(scene)))
    export = read_pipeline_state(scene).annotation_export
    assert export is not None
    assert export.emitters[0].success


def test_failed_reasoning_records_state_before_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    media = tmp_path / "clip.mp4"
    media.touch()
    scene = tmp_path / "scene"
    task = ReasoningTask(config=DaftExportConfig(events=EventsConfig(enabled=True)))
    monkeypatch.setattr(task.resolver, "resolve_llm", lambda: (None, None))
    with pytest.raises(RuntimeError, match="every enabled stage"):
        task.run(DataEntry(media_path=str(media), data_path=str(scene)))
    export = read_pipeline_state(scene).annotation_export
    assert export is not None
    assert export.emitters[0].success is False
