# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from core import (
    DataEntry,
    EnhancedMediaState,
    SceneContext,
    ScenePaths,
    ScenePipelineState,
    read_pipeline_state,
    write_pipeline_state,
)
from detection_and_tracking import (
    DetectionAndTrackingConfig,
    DetectionAndTrackingTask,
    StubTracker,
    factory,
)
from detection_and_tracking.artifacts import TRACKING_ARTIFACTS_KEY, TrackingArtifactsState
from detection_and_tracking.backends.runtime import instances_json_path, objects_json_path
from detection_and_tracking.factory import (
    TRACKER_ENTRY_POINT_GROUP,
    create_tracker,
    list_trackers,
    load_entry_point_trackers,
    register_tracker,
)
from detection_and_tracking.tracker import Tracker, TrackingResult


class _CaptureTracker(Tracker):
    def __init__(self) -> None:
        super().__init__(logger=logging.getLogger("test_capture_tracker"))
        self.seen_media_path: Path | None = None

    def run(
        self,
        media_path: Path,
        scene_paths: ScenePaths,
        *,
        scene_ctx: SceneContext,
    ) -> TrackingResult:
        _ = scene_ctx
        self.seen_media_path = media_path
        objects_json = objects_json_path(scene_paths)
        instances_json = instances_json_path(scene_paths)
        objects_json.write_text("{}", encoding="utf-8")
        instances_json.write_text("{}", encoding="utf-8")
        return TrackingResult(
            success=True,
            objects_json=objects_json,
            instances_json=instances_json,
        )


def test_stub_tracker_emits_daft_artifacts(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.touch()
    data = tmp_path / "scene"

    task = DetectionAndTrackingTask(
        config=DetectionAndTrackingConfig(tracker="stub"),
    )
    task.run(DataEntry(media_path=str(media), data_path=str(data)))

    objects = data / "contextual" / "objects.json"
    instances = data / "contextual" / "instances.json"
    assert objects.exists() and instances.exists()
    raw_media = data / "raw" / "clip.mp4"
    assert raw_media.is_symlink()
    assert raw_media.resolve() == media.resolve()
    objects_payload = json.loads(objects.read_text())
    assert objects_payload["version"] == "metropolis-v3.0"
    assert objects_payload["video_id"] == "clip"
    assert objects_payload["frames"] == []

    pipeline_state = read_pipeline_state(data)
    tracking_artifacts = TrackingArtifactsState.model_validate(
        pipeline_state.task_artifacts[TRACKING_ARTIFACTS_KEY]
    )
    assert tracking_artifacts.success is True
    assert tracking_artifacts.objects_json == str(objects)


def test_stub_tracker_uses_persisted_media_id_for_staged_active_media(
    tmp_path: Path,
) -> None:
    data = tmp_path / "pipeline_data_tmp"
    active = data / "sidecars" / "active.mp4"
    active.parent.mkdir(parents=True)
    active.touch()
    write_pipeline_state(data, ScenePipelineState(media_id="clip_001"))

    task = DetectionAndTrackingTask(
        config=DetectionAndTrackingConfig(tracker="stub"),
    )
    task.run(DataEntry(media_path=str(active), data_path=str(data)))

    objects_payload = json.loads((data / "contextual" / "objects.json").read_text())
    assert objects_payload["video_id"] == "clip_001"


def test_task_can_copy_raw_media(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    data = tmp_path / "scene"

    task = DetectionAndTrackingTask(
        config=DetectionAndTrackingConfig(tracker="stub", copy_media=True),
    )
    task.run(DataEntry(media_path=str(media), data_path=str(data)))

    raw_media = data / "raw" / "clip.mp4"
    assert raw_media.exists()
    assert not raw_media.is_symlink()
    assert raw_media.read_bytes() == b"media"


def test_disabled_task_is_noop(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.touch()
    data = tmp_path / "scene"
    task = DetectionAndTrackingTask(
        config=DetectionAndTrackingConfig(enabled=False),
        tracker=StubTracker(logger=logging.getLogger("test_disabled_tracker")),
    )
    task.run(DataEntry(media_path=str(media), data_path=str(data)))
    assert not (data / "contextual" / "objects.json").exists()


def test_builtin_tracker_kinds_are_registered() -> None:
    kinds = list_trackers()
    assert kinds == ["rfdetr-boosttrack", "rfdetr-bytetrack", "sam3", "stub"]


def test_deepocsort_tracker_kind_still_fails_loudly() -> None:
    with pytest.raises(NotImplementedError, match="planned but not implemented"):
        create_tracker("rfdetr-deepocsort", logger=logging.getLogger("test_deepocsort"))


def _unregister_on_teardown(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    """Keep test-registered kinds out of the process-wide tracker registry."""
    builders = factory._REGISTRY._builders
    assert kind not in builders
    monkeypatch.setitem(builders, kind, builders["stub"])
    del builders[kind]


def test_unknown_tracker_kind_is_rejected_when_created_with_registered_list() -> None:
    # The config accepts any kind so plug-in backends need no edit here (CDF-06);
    # the registry rejects unknown kinds and names the registered ones.
    """Reject unknown trackers at construction and list the registered alternatives."""
    config = DetectionAndTrackingConfig(tracker="unknown")
    with pytest.raises(ValueError, match=r"Unknown tracker kind: 'unknown'\. Registered: .*stub"):
        create_tracker(config.tracker, logging.getLogger("test_unknown"), config)


def test_registered_plugin_tracker_runs_without_editing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow a registered external tracker through configuration and construction."""

    class _DummyTracker(StubTracker):
        """Represent an externally registered tracker using the stub implementation."""

        pass

    _unregister_on_teardown(monkeypatch, "dummy-plugin")
    register_tracker("dummy-plugin", lambda logger, _config: _DummyTracker(logger))
    config = DetectionAndTrackingConfig(tracker="dummy-plugin")

    tracker = create_tracker(config.tracker, logging.getLogger("test_dummy"), config)

    assert isinstance(tracker, _DummyTracker)
    assert "dummy-plugin" in list_trackers()


def test_entry_point_trackers_register_and_bad_plugins_are_skipped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Register loadable plug-ins while reporting and skipping broken entry points."""

    class _EntryPoint:
        """Provide a controllable entry point for plug-in loading tests."""

        def __init__(self, name: str, builder: object) -> None:
            """Store the entry point identity and its builder or import error."""
            self.name = name
            self.value = f"plugin:{name}"
            self._builder = builder

        def load(self) -> object:
            """Return the test builder or raise its configured import failure."""
            if isinstance(self._builder, Exception):
                raise self._builder
            return self._builder

    def builder(logger: logging.Logger, _config: DetectionAndTrackingConfig) -> StubTracker:
        """Construct the stub tracker exposed by the test entry point."""
        return StubTracker(logger)

    groups: list[str] = []

    def fake_entry_points(*, group: str) -> list[_EntryPoint]:
        """Record the requested group and return working and broken plug-ins."""
        groups.append(group)
        return [
            _EntryPoint("ep-tracker", builder),
            _EntryPoint("broken", ImportError("no")),
            _EntryPoint("not-callable", object()),
        ]

    monkeypatch.setattr("detection_and_tracking.factory.entry_points", fake_entry_points)
    _unregister_on_teardown(monkeypatch, "ep-tracker")

    with caplog.at_level(logging.WARNING, logger="test_ep"):
        loaded = load_entry_point_trackers(logging.getLogger("test_ep"))

    assert groups == [TRACKER_ENTRY_POINT_GROUP]
    assert loaded == ["ep-tracker"]
    assert "ep-tracker" in list_trackers()
    assert "broken" not in list_trackers()
    assert "not-callable" not in list_trackers()
    assert "Skipping tracker plug-in 'not-callable' (plugin:not-callable)" in caplog.text
    assert "Skipping tracker plug-in 'broken'" in caplog.text


def test_sam3_requires_prompts() -> None:
    with pytest.raises(ValueError, match="requires sam3_prompts"):
        create_tracker("sam3", logger=logging.getLogger("test_sam3"))


def test_task_uses_enhanced_media_when_available(tmp_path: Path) -> None:
    original = tmp_path / "clip.mp4"
    original.touch()
    enhanced = tmp_path / "sr.mp4"
    enhanced.touch()
    data = tmp_path / "scene"
    write_pipeline_state(
        data,
        ScenePipelineState(
            enhanced_media=EnhancedMediaState(success=True, output_path=str(enhanced))
        ),
    )
    tracker = _CaptureTracker()
    task = DetectionAndTrackingTask(
        config=DetectionAndTrackingConfig(tracker="stub"), tracker=tracker
    )

    task.run(DataEntry(media_path=str(original), data_path=str(data)))

    assert tracker.seen_media_path == enhanced


def test_task_ignores_missing_enhanced_media(tmp_path: Path) -> None:
    original = tmp_path / "clip.mp4"
    original.touch()
    missing = tmp_path / "missing_sr.mp4"
    data = tmp_path / "scene"
    write_pipeline_state(
        data,
        ScenePipelineState(
            enhanced_media=EnhancedMediaState(success=True, output_path=str(missing))
        ),
    )
    tracker = _CaptureTracker()
    task = DetectionAndTrackingTask(
        config=DetectionAndTrackingConfig(tracker="stub"), tracker=tracker
    )

    task.run(DataEntry(media_path=str(original), data_path=str(data)))

    assert tracker.seen_media_path == original


def test_tracker_plugin_can_import_public_exports() -> None:
    """Load a plug-in in a fresh process while the package is still importing."""
    code = """
from importlib import metadata
class EntryPoint:
    name = "config-import-plugin"
    value = "plugin:build"
    def load(self):
        from detection_and_tracking import (
            DetectionAndTrackingConfig, Tracker, TrackingResult, StubTracker, create_tracker,
        )
        assert Tracker is not None and TrackingResult is not None
        assert StubTracker is not None and callable(create_tracker)
        assert DetectionAndTrackingConfig().tracker
        return lambda logger, config: None
original = metadata.entry_points
metadata.entry_points = lambda **kw: (
    [EntryPoint()] if kw.get("group") == "cdf.trackers" else original(**kw)
)
import detection_and_tracking as package
assert "config-import-plugin" in package.list_trackers()
assert "stub" in package.list_trackers()
assert package.StubTracker is not None
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=os.environ.copy()
    )
    assert result.returncode == 0, result.stdout + result.stderr
