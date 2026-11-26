# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Configuration must behave like explicitly supplied CLI arguments."""

import json
from pathlib import Path

import pytest
from core.interfaces.config_args import ServiceArgumentParser, override_config, read_config


def parser() -> ServiceArgumentParser:
    result = ServiceArgumentParser(allow_abbrev=False)
    result.add_argument("--count", type=int, default=2)
    result.add_argument("--mode", choices=["video", "frames"], default="video")
    result.add_argument("--enabled", action="store_true")
    result.add_argument("--classes", nargs="*", default=[])
    result.add_argument("--format", dest="formats", action="append", required=True)
    group = result.add_mutually_exclusive_group()
    group.add_argument("--input")
    group.add_argument("--input-file")
    result.configure()
    return result


def config(tmp_path: Path, value: object) -> list[str]:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(value))
    return ["--config-file", str(path)]


def test_config_required_types_and_cli_replacement(tmp_path: Path) -> None:
    argv = config(
        tmp_path,
        {
            "count": 3,
            "enabled": True,
            "classes": ["car", "truck"],
            "format": ["old"],
            "input_file": "old.jsonl",
        },
    )
    result = parser().parse_args(
        argv
        + [
            "--count",
            "4",
            "--no-enabled",
            "--classes",
            "person",
            "--format",
            "new",
            "--input",
            "[]",
        ]
    )
    assert result.count == 4
    assert result.enabled is False
    assert result.classes == ["person"]
    assert result.formats == ["new"]
    assert result.input_file is None
    assert result.input == "[]"


def test_yaml_and_set_precedence(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("count: 3\nformat: [one]\nenabled: false\n")
    result = parser().parse_args(["--config-file", str(path), "--set", "count=5", "--count", "6"])
    assert result.count == 6
    assert result.formats == ["one"]
    assert result.enabled is False


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"typo": 1},
        {"count": "invalid"},
        {"mode": "unknown"},
        {"enabled": "false"},
        {"classes": "car"},
        {"classes": ["--enabled"]},
        {"format": "one"},
        {"count": None},
        {"config_file": "nested.json"},
        {"input": "[]", "input_file": "x"},
    ],
)
def test_invalid_config_fails(tmp_path: Path, value: object) -> None:
    with pytest.raises(SystemExit):
        parser().parse_args(
            config(tmp_path, {"format": ["test"], **value} if isinstance(value, dict) else value)
        )


def test_nested_overrides_do_not_mutate_source() -> None:
    source = {"events": {"enabled": True, "max_tokens": 100}}
    result = override_config(
        source,
        ["events.enabled=false", "events.max_tokens=42", 'open_qa.questions=["What happened?"]'],
    )
    assert result["events"] == {"enabled": False, "max_tokens": 42}
    assert result["open_qa"]["questions"] == ["What happened?"]
    assert source["events"]["enabled"] is True


@pytest.mark.parametrize(
    "assignment", ["missing", "=1", "events..enabled=true", "events.enabled=true"]
)
def test_malformed_or_scalar_path_override_fails(assignment: str) -> None:
    with pytest.raises(ValueError):
        override_config({"events": 5}, [assignment])


def test_native_config_only_uses_cli_section(tmp_path: Path) -> None:
    result = parser()
    result.native_config = True
    args = result.parse_args(
        config(tmp_path, {"events": {"enabled": True}, "cli": {"format": ["one"], "count": 7}})
        + ["--set", "events.enabled=false"]
    )
    assert args.count == 7
    assert args.config_overrides == ["events.enabled=false"]


def test_help_does_not_require_config_or_required_arguments() -> None:
    with pytest.raises(SystemExit) as caught:
        parser().parse_args(["--config-file", "missing.yaml", "--help"])
    assert caught.value.code == 0


def test_set_uses_same_aliases_as_file(tmp_path: Path) -> None:
    args = parser().parse_args(config(tmp_path, {"formats": ["old"]}) + ["--set", 'format=["new"]'])
    assert args.formats == ["new"]


@pytest.mark.parametrize("cli", [[], {1: "invalid"}])
def test_native_cli_section_rejects_invalid_shape(tmp_path: Path, cli: object) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("cli: []" if isinstance(cli, list) else "cli: {1: invalid}")
    result = parser()
    result.native_config = True
    with pytest.raises(SystemExit):
        result.parse_args(["--config-file", str(path)])


def test_config_expands_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "reasoning.yaml").write_text("events: {enabled: true}")
    assert read_config("~/reasoning.yaml") == {"events": {"enabled": True}}


@pytest.mark.parametrize("value", ["-h", "-x", "--help", "--"])
def test_list_option_values_are_rejected(tmp_path: Path, value: str) -> None:
    with pytest.raises(SystemExit) as caught:
        parser().parse_args(config(tmp_path, {"classes": [value], "format": ["one"]}))
    assert caught.value.code == 2


def test_negative_numeric_list_values_are_preserved(tmp_path: Path) -> None:
    args = parser().parse_args(config(tmp_path, {"classes": ["-1", "normal"], "format": ["one"]}))
    assert args.classes == ["-1", "normal"]


@pytest.mark.parametrize(
    ("assignment", "expected"),
    [
        ('events={"enabled":false}', {"enabled": False}),
        ('events.labels=["person"]', {"enabled": True, "labels": ["person"]}),
        ("events=null", None),
    ],
)
def test_overrides_replace_assigned_containers(assignment: str, expected: object) -> None:
    source = {"events": {"enabled": True, "labels": ["car", "truck"]}}
    assert override_config(source, [assignment])["events"] == expected
    assert source == {"events": {"enabled": True, "labels": ["car", "truck"]}}


@pytest.mark.parametrize("value", ["yes", "001", "${oc.env:SECRET}", "???", "a=b"])
def test_override_strings_remain_literal(value: str) -> None:
    assert override_config({"prompt": "${missing}"}, [f"label={value}"]) == {
        "prompt": "${missing}",
        "label": value,
    }


def test_overrides_create_null_sections_and_apply_in_order() -> None:
    assert override_config({"events": None}, ["events.enabled=false", "events.enabled=true"]) == {
        "events": {"enabled": True}
    }


def test_nested_override_does_not_follow_interpolated_section() -> None:
    with pytest.raises(ValueError, match="Cannot override nested field"):
        override_config(
            {"events": "${other}", "other": {"enabled": False}}, ["events.enabled=true"]
        )
