# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Every packaged service uses the same configuration precedence."""

import importlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest
from core import DataEntry
from core.utils.multistorage import MSCStorage
from event_and_person_attribute_search_service.main import (
    EventAndPersonAttributeSearchService,
    _apply_cli_overrides,
)
from event_and_person_attribute_search_service.main import _load_config as load_pas
from pydantic import BaseModel, ValidationError
from reasoning_service.main import ReasoningService
from reasoning_service.main import _apply_cli_overrides as merge_reasoning
from reasoning_service.main import _load_config as load_reasoning
from workflow_runner.main import WorkflowRunnerService

SERVICES = [
    ("captioning", "CaptioningService"),
    ("detection_and_tracking", "DetectionAndTrackingService"),
    ("event_and_person_attribute_search", "EventAndPersonAttributeSearchService"),
    ("example", "ExampleService"),
    ("grounding_2d", "Grounding2DService"),
    ("reasoning", "ReasoningService"),
    ("referring_expressions", "ReferringExpressionsService"),
    ("super_resolution", "SuperResolutionService"),
    ("training_export", "TrainingExportService"),
    ("visual_qa", "VisualQaService"),
    ("workflow_runner", "WorkflowRunnerService"),
]


@pytest.mark.parametrize(("name", "class_name"), SERVICES)
@pytest.mark.parametrize("explicit", [False, True])
def test_every_service_loads_config_and_accepts_overrides(
    tmp_path: Path, name: str, class_name: str, explicit: bool
) -> None:
    package = name if name == "workflow_runner" else name + "_service"
    service = getattr(importlib.import_module(package + ".main"), class_name)()
    settings = {
        "log_level": "DEBUG",
        "input": [{"id": "test", "media_path": "video.mp4", "data_path": "scene"}],
    }
    if name == "training_export":
        settings.update(training_export_format=["cosmos-reason-v1.0"], training_export_dir="export")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"cli": settings} if service.native_config else settings))
    argv = ["--config-file", str(path)]
    if explicit:
        argv += ["--log-level", "ERROR"]
    args = service.build_parser().parse_args(argv)
    assert args.log_level == ("ERROR" if explicit else "DEBUG")
    assert json.loads(args.input)[0]["id"] == "test"
    if name == "training_export":
        assert args.training_export_formats == ["cosmos-reason-v1.0"]


def test_reasoning_overrides_can_supply_required_fields(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"open_qa": {"enabled": True}}))
    result = load_reasoning(
        path, ['open_qa.questions=["What happened?"]', "open_qa.temperature=0.2"]
    )
    assert result.open_qa is not None
    assert result.open_qa.questions == ["What happened?"]
    assert result.open_qa.temperature == 0.2
    with pytest.raises(ValidationError):
        load_reasoning(path, ['open_qa.questions=["What happened?"]', "open_qa.typo=1"])


def test_reasoning_direct_and_cookbook_formats(tmp_path: Path) -> None:
    for raw in [
        {"reasoning": {"enabled": True}},
        {"pipeline": "video", "reasoning": {"reasoning": {"enabled": True}}},
    ]:
        path = tmp_path / "config.json"
        path.write_text(json.dumps(raw))
        result = load_reasoning(path, ["reasoning.enabled=false"])
        assert result.reasoning is not None
        assert not result.reasoning.enabled


def test_pas_overrides_cover_fields_without_named_flags(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"person_attribute_search": {"easy_count": 2}, "cli": {"log_level": "INFO"}})
    )
    result = load_pas(path, ["easy_count=0", 'caption_sidecars=["captioning/video_captions.json"]'])
    assert result.easy_count == 0
    assert result.caption_sidecars == ("captioning/video_captions.json",)
    with pytest.raises(ValidationError):
        load_pas(path, ["easy_count=-1"])


def test_pas_file_cli_set_and_explicit_flag_precedence(tmp_path: Path) -> None:
    path = tmp_path / "pas.json"
    path.write_text(json.dumps({"cli": {"query_count": 3}, "bundle_query_count": 2}))
    parser = EventAndPersonAttributeSearchService().build_parser()
    argv = ["--config-file", str(path), "--set", "bundle_query_count=4"]
    args = parser.parse_args(argv)
    assert _apply_cli_overrides(load_pas(path), args).bundle_query_count == 4
    args = parser.parse_args(argv + ["--query-count", "5"])
    assert _apply_cli_overrides(load_pas(path), args).bundle_query_count == 5


@pytest.mark.parametrize(("name", "class_name"), SERVICES)
def test_service_cli_entrypoint_exposes_config(name: str, class_name: str) -> None:
    package = name if name == "workflow_runner" else name + "_service"
    result = subprocess.run(
        [sys.executable, "-m", package + ".main", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--config-file" in result.stdout
    assert "--set" in result.stdout


def test_empty_reasoning_section_in_existing_cookbook(tmp_path: Path) -> None:
    path = tmp_path / "cookbook.json"
    path.write_text(json.dumps({"pipeline": "video", "reasoning": {}}))
    assert load_reasoning(path).events is None


@pytest.mark.parametrize(
    ("overrides", "expected_count"),
    [
        (["--set", "easy_count=0", "--set", "bundle_query_count=3"], 3),
        (["--set", "easy_count=0", "--query-count", "4"], 4),
    ],
)
def test_pas_execute_merges_before_validation(
    tmp_path: Path, overrides: list[str], expected_count: int
) -> None:
    path = tmp_path / "pas.json"
    path.write_text(json.dumps({"easy_count": -1, "bundle_query_count": -1}))
    service = EventAndPersonAttributeSearchService()
    args = service.build_parser().parse_args(["--config-file", str(path), *overrides])
    with patch.object(service, "_execute_pipeline") as execute:
        service.execute(args, [])
    merged = execute.call_args.args[0]
    assert merged.easy_count == 0
    assert merged.bundle_query_count == expected_count
    with pytest.raises(ValidationError):
        service.execute(service.build_parser().parse_args(["--config-file", str(path)]), [])


def test_reasoning_rejects_unknown_sibling_in_direct_config(tmp_path: Path) -> None:
    path = tmp_path / "reasoning.json"
    path.write_text(
        json.dumps(
            {
                "events": {"enabled": True},
                "reasoning": {"enabled": False},
                "evnets": {"enabled": True},
            }
        )
    )
    with pytest.raises(ValidationError, match="evnets"):
        load_reasoning(path)


def test_remote_reasoning_config_survives_execution(tmp_path: Path) -> None:
    downloaded: list[Path] = []
    url = "msc://test/reasoning.yaml"

    def download(_storage: MSCStorage, source: str, local: str, *, is_file: bool) -> str:
        assert source == url and is_file
        path = Path(local)
        assert not downloaded, "The config must only be downloaded once."
        path.write_text(
            "cli: {llm_model: original-model}\nevents: {enabled: false, max_tokens: 123}"
        )
        downloaded.append(path)
        return str(path)

    service = ReasoningService()
    with patch.object(MSCStorage, "download_if_remote", download):
        args = service.build_parser().parse_args(["--config-file", url])
        assert not downloaded[0].exists()
        assert args.llm_model == "original-model"
        with (
            patch("reasoning_service.main.LinearPipeline") as pipeline,
            patch("reasoning_service.main.ReasoningTask") as task,
        ):

            def run(entries: list[DataEntry]) -> list[DataEntry]:
                config_dir = task.call_args.kwargs["config_dir"]
                assert (config_dir / "config.yaml").exists()
                assert task.call_args.kwargs["config"].events.max_tokens == 123
                return entries

            pipeline.return_value.run.side_effect = run
            service.execute(args, [])
            assert not task.call_args.kwargs["config_dir"].exists()
    assert len(downloaded) == 1
    assert not downloaded[-1].exists()


@pytest.mark.parametrize("use_file", [False, True])
def test_cookbook_cannot_replace_configured_stage_selection(tmp_path: Path, use_file: bool) -> None:
    cookbook = tmp_path / "cookbook.json"
    cookbook.write_text(json.dumps({"pipeline": "video", "stages": ["captioning", "reasoning"]}))
    argv = ["--cookbook-file", str(cookbook), "--container-dry-run"]
    if use_file:
        config_path = tmp_path / "service.json"
        config_path.write_text(json.dumps({"stages": ["captioning"]}))
        argv += ["--config-file", str(config_path)]
    else:
        argv += ["--set", 'stages=["captioning"]']
    service = WorkflowRunnerService()
    args = service.build_parser().parse_args(argv)
    with patch("workflow_runner.main.ContainerPipelineRunner") as runner:
        service.execute(
            args, [DataEntry(media_path="video.mp4", data_path=str(tmp_path / "scene"))]
        )
    stages = runner.return_value.run.call_args.args[0]
    assert [stage.name for stage in stages] == ["captioning"]


def test_reasoning_uses_parsed_snapshot_if_local_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "reasoning.json"
    path.write_text(json.dumps({"events": {"enabled": False, "max_tokens": 123}}))
    service = ReasoningService()
    args = service.build_parser().parse_args(["--config-file", str(path)])
    path.write_text(json.dumps({"events": {"enabled": False, "max_tokens": 999}}))
    with (
        patch("reasoning_service.main.LinearPipeline"),
        patch("reasoning_service.main.ReasoningTask") as task,
    ):
        service.execute(args, [])
    assert task.call_args.kwargs["config"].events.max_tokens == 123
    assert task.call_args.kwargs["config_dir"] == tmp_path


def test_reasoning_named_flags_replace_tasks_and_repair_config(tmp_path: Path) -> None:
    path = tmp_path / "reasoning.json"
    path.write_text(
        json.dumps(
            {
                "events": {"enabled": True, "temperature": -1},
                "anomaly": {"enabled": True},
            }
        )
    )
    args = (
        ReasoningService()
        .build_parser()
        .parse_args(
            [
                "--config-file",
                str(path),
                "--tasks",
                "events",
                "--set",
                "events.temperature=0.8",
                "--temperature",
                "0.2",
                "--max-tokens",
                "128",
                "--llm-retries",
                "0",
            ]
        )
    )
    result = load_reasoning(path, args=args)
    assert result.events is not None
    assert result.events.enabled
    assert result.events.temperature == 0.2
    assert result.events.max_tokens == 128
    assert result.events.retries == 0
    assert result.anomaly is not None
    assert not result.anomaly.enabled
    assert result.anomaly.max_tokens == 1024


def test_reasoning_named_inputs_without_config_do_not_enable_tasks(tmp_path: Path) -> None:
    bank = str(tmp_path / "questions.json")
    parser = ReasoningService().build_parser()
    args = parser.parse_args(["--open-qa-question-file", bank, "--temperature", "0.3"])
    result = merge_reasoning({}, args)
    assert result.open_qa is not None
    assert not result.open_qa.enabled
    assert result.open_qa.temperature == 0.0
    args = parser.parse_args(
        [
            "--tasks",
            "open_qa",
            "--open-qa-question-file",
            bank,
            "--temperature",
            "0.3",
        ]
    )
    result = merge_reasoning({}, args)
    assert result.open_qa is not None
    assert result.open_qa.enabled
    assert result.open_qa.question_file == bank
    assert result.open_qa.temperature == 0.3


def test_reasoning_file_cli_defaults_yield_to_set(tmp_path: Path) -> None:
    path = tmp_path / "reasoning.json"
    path.write_text(json.dumps({"cli": {"tasks": ["events"], "temperature": 0.1}}))
    args = (
        ReasoningService()
        .build_parser()
        .parse_args(
            [
                "--config-file",
                str(path),
                "--set",
                "events.temperature=0.4",
            ]
        )
    )
    result = load_reasoning(path, snapshot=args.config_snapshot, args=args)
    assert result.events is not None
    assert result.events.temperature == 0.4


def test_pas_reuses_snapshot_without_downloading_again(tmp_path: Path) -> None:
    service = EventAndPersonAttributeSearchService()
    path = tmp_path / "pas.json"
    path.write_text(json.dumps({"bundle_query_count": 3}))
    args = service.build_parser().parse_args(["--config-file", str(path)])
    path.unlink()
    args.config_file = "msc://test/pas.json"
    with (
        patch.object(service.storage, "download_if_remote") as download,
        patch.object(service, "_execute_pipeline") as pipeline,
    ):
        service.execute(args, [])
    download.assert_not_called()
    assert pipeline.call_args.args[0].bundle_query_count == 3


@pytest.mark.parametrize("override", [["--llm-model", "chosen"], ["--llm-model=chosen"]])
def test_reasoning_explicit_model_overrides_config_null(
    tmp_path: Path, override: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "reasoning.json"
    path.write_text(json.dumps({"cli": {"llm_model": None}}))
    parser = ReasoningService().build_parser()
    argv = ["--config-file", str(path)]
    assert parser.parse_args(argv + override).llm_model == "chosen"
    with pytest.raises(SystemExit):
        parser.parse_args(argv)
    assert "llm_model does not accept null" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("overrides", "flags", "expected"),
    [
        (["events.enabled=true"], [], 0.1),
        (['events={"enabled":true}'], [], 0.1),
        (["events.enabled=true", "events.temperature=0.4"], [], 0.4),
        (["events.enabled=true", "events.temperature=0.4"], ["--temperature", "0.7"], 0.7),
    ],
)
def test_reasoning_newly_enabled_task_uses_file_cli_defaults(
    tmp_path: Path, overrides: list[str], flags: list[str], expected: float
) -> None:
    path = tmp_path / "reasoning.json"
    path.write_text(json.dumps({"cli": {"temperature": 0.1}}))
    argv = ["--config-file", str(path)]
    for assignment in overrides:
        argv.extend(["--set", assignment])
    args = ReasoningService().build_parser().parse_args(argv + flags)
    result = load_reasoning(path, snapshot=args.config_snapshot, args=args)
    assert result.events is not None and result.events.enabled
    assert result.events.temperature == expected


@pytest.mark.parametrize("loader", [load_pas, load_reasoning])
def test_native_config_loaders_use_shared_path_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, loader: Callable[[Path], BaseModel]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "settings.yaml").write_text("{}")
    assert loader(Path("~/settings.yaml")) == loader(tmp_path / "settings.yaml")


@pytest.mark.parametrize("loader", [load_pas, load_reasoning])
def test_native_config_loaders_reject_non_string_keys(
    tmp_path: Path, loader: Callable[[Path], BaseModel]
) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("1: value")
    with pytest.raises(ValueError, match="string keys"):
        loader(path)
