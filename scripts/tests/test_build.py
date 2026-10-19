# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for scripts/build.py"""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from build import (
    DEFAULT_BUILD_PLATFORMS,
    BuildableImage,
    BuildOptions,
    _redact_build_args,
    _registry_cache_ref,
    _select_image_with_text_prompt,
    _single_platform_arch,
    choose_image,
    discover_buildable_images,
    execute_build,
    format_image_list,
    main,
    parse_args,
)


@pytest.fixture
def two_images(tmp_path: Path) -> list[BuildableImage]:
    return [
        BuildableImage(
            target="pkg-a:main",
            project_name="pkg-a",
            version="1.2.3",
            package_dir=tmp_path / "packages" / "pkg-a",
            image_name="main",
            command="docker build -t pkg-a -f packages/pkg-a/docker/Dockerfile .",
        ),
        BuildableImage(
            target="pkg-b:gpu",
            project_name="pkg-b",
            version="4.5.6",
            package_dir=tmp_path / "packages" / "pkg-b",
            image_name="gpu",
            command="docker build -t pkg-b-gpu -f packages/pkg-b/docker/Dockerfile .",
        ),
    ]


# --- parse_args ---


def test_parse_args_no_args() -> None:
    options = parse_args([])
    assert options == BuildOptions(
        target=None,
        list_images=False,
        output_format="text",
        tag=None,
        push=False,
        platforms=DEFAULT_BUILD_PLATFORMS,
    )


def test_parse_args_positional() -> None:
    options = parse_args(["pkg-a:main"])
    assert options.target == "pkg-a:main"


def test_parse_args_list_json() -> None:
    options = parse_args(["--list", "--format", "json"])
    assert options == BuildOptions(
        target=None,
        list_images=True,
        output_format="json",
        tag=None,
        push=False,
        platforms=DEFAULT_BUILD_PLATFORMS,
    )


def test_parse_args_tag_and_push() -> None:
    options = parse_args(["pkg-a:main", "--tag", "registry/pkg-a:tag", "--push"])
    assert options == BuildOptions(
        target="pkg-a:main",
        list_images=False,
        output_format="text",
        tag="registry/pkg-a:tag",
        push=True,
        platforms=DEFAULT_BUILD_PLATFORMS,
    )


def test_parse_args_platform_override() -> None:
    options = parse_args(["pkg-a:main", "--platform", "linux/arm64"])
    assert options.platforms == "linux/arm64"


def test_parse_args_rejects_empty_platform_value() -> None:
    with pytest.raises(ValueError, match="--platform"):
        parse_args(["pkg-a:main", "--platform", ""])


def test_parse_args_rejects_whitespace_platform_value() -> None:
    with pytest.raises(ValueError, match="--platform"):
        parse_args(["pkg-a:main", "--platform", "   "])


def test_parse_args_rejects_empty_tag_value() -> None:
    with pytest.raises(ValueError, match="--tag"):
        parse_args(["pkg-a:main", "--tag", ""])


def test_parse_args_rejects_empty_tag_equals_value() -> None:
    with pytest.raises(ValueError, match="--tag"):
        parse_args(["pkg-a:main", "--tag="])


def test_parse_args_rejects_extra_args_without_separator() -> None:
    with pytest.raises(ValueError, match="Expected at most one build target"):
        parse_args(["pkg-a:main", "pkg-b:gpu"])


def test_parse_args_rejects_unknown_options() -> None:
    with pytest.raises(ValueError, match="Unknown option"):
        parse_args(["pkg-a:main", "--no-cache"])


def test_parse_args_rejects_format_without_list() -> None:
    with pytest.raises(ValueError, match="--format"):
        parse_args(["pkg-a:main", "--format", "json"])


def test_parse_args_rejects_explicit_format_matching_default() -> None:
    # "text" is also the default, so this must not slip past the
    # output_format != TEXT_FORMAT check.
    with pytest.raises(ValueError, match="--format"):
        parse_args(["pkg-a:main", "--format", "text"])


def test_parse_args_rejects_list_with_tag() -> None:
    with pytest.raises(ValueError, match="--tag"):
        parse_args(["--list", "--tag", "registry/pkg-a:tag"])


# --- choose_image ---


def test_choose_image_by_name(two_images: list[BuildableImage]) -> None:
    result = choose_image(two_images, "pkg-a:main")
    assert result.target == "pkg-a:main"


def test_choose_image_unknown_name_raises(two_images: list[BuildableImage]) -> None:
    with pytest.raises(ValueError, match="Unknown target"):
        choose_image(two_images, "missing:image")


def test_choose_image_no_tty_raises(two_images: list[BuildableImage]) -> None:
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False
        with pytest.raises(ValueError, match="No target was specified"):
            choose_image(two_images, None)


def test_choose_image_interactive_selection(two_images: list[BuildableImage]) -> None:
    with (
        patch("sys.stdin") as mock_stdin,
        patch("build._select_image_interactively", return_value="pkg-b:gpu"),
    ):
        mock_stdin.isatty.return_value = True
        result = choose_image(two_images, None)
        assert result.target == "pkg-b:gpu"


def test_choose_image_interactive_cancelled_raises(two_images: list[BuildableImage]) -> None:
    with (
        patch("sys.stdin") as mock_stdin,
        patch("build._select_image_interactively", return_value=None),
    ):
        mock_stdin.isatty.return_value = True
        with pytest.raises(KeyboardInterrupt):
            choose_image(two_images, None)


def test_text_prompt_selection_returns_selected_image(two_images: list[BuildableImage]) -> None:
    with patch("builtins.input", return_value="2"), patch("builtins.print"):
        assert _select_image_with_text_prompt(two_images) == "pkg-b:gpu"


def test_text_prompt_selection_rejects_out_of_range_index(
    two_images: list[BuildableImage],
) -> None:
    with patch("builtins.input", return_value="3"), patch("builtins.print"):
        with pytest.raises(ValueError, match="outside the valid range"):
            _select_image_with_text_prompt(two_images)


# --- discover_buildable_images ---


def _make_workspace(tmp_path: Path, members_toml: str) -> Path:
    root_pyproject = tmp_path / "pyproject.toml"
    root_pyproject.write_text(f"[tool.uv.workspace]\nmembers = {members_toml}\n")
    return root_pyproject


def _make_package(tmp_path: Path, package_path: str, pyproject_text: str) -> Path:
    package_dir = tmp_path / package_path
    package_dir.mkdir(parents=True)
    (package_dir / "pyproject.toml").write_text(pyproject_text)
    return package_dir


def test_discover_buildable_images_finds_command_string(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["services/*"]')
    _make_package(
        tmp_path,
        "services/example_service",
        "[project]\n"
        'name = "example-service"\n'
        'version = "0.1.0"\n'
        "[tool.build.images]\n"
        'build = "docker build -t example-service '
        "--build-arg PACKAGE_NAME=example-service "
        '-f services/example_service/docker/Dockerfile ."\n',
    )
    # Second service ensures we do not assume a single registered image.
    _make_package(
        tmp_path,
        "services/other_service",
        "[project]\n"
        'name = "other-service"\n'
        'version = "0.2.0"\n'
        "[tool.build.images]\n"
        'build = "docker build -t other-service '
        "--build-arg PACKAGE_NAME=other-service "
        '-f services/other_service/docker/Dockerfile ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        images = discover_buildable_images()

    by_target = {image.target: image for image in images}
    assert by_target["example-service:build"].command == (
        "docker build -t example-service --build-arg PACKAGE_NAME=example-service "
        "-f services/example_service/docker/Dockerfile ."
    )
    assert by_target["other-service:build"].project_name == "other-service"


def test_discover_buildable_images_multiple_images_per_package(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["services/*"]')
    _make_package(
        tmp_path,
        "services/multi",
        "[project]\n"
        'name = "multi"\n'
        'version = "1.0.0"\n'
        "[tool.build.images]\n"
        'main = "docker build -t multi ."\n'
        'gpu = "docker build --build-arg ACCELERATOR=gpu -t multi-gpu ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        images = discover_buildable_images()

    by_target = {image.target: image for image in images}
    assert by_target["multi:main"].command == "docker build -t multi ."
    assert by_target["multi:gpu"].command == (
        "docker build --build-arg ACCELERATOR=gpu -t multi-gpu ."
    )


def test_discover_buildable_images_preserves_quoted_command_values(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["services/*"]')
    _make_package(
        tmp_path,
        "services/quoted",
        "[project]\n"
        'name = "quoted"\n'
        'version = "1.0.0"\n'
        "[tool.build.images]\n"
        "main = \"docker build --label description='example service' -t quoted .\"\n",
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        images = discover_buildable_images()

    by_target = {image.target: image for image in images}
    assert by_target["quoted:main"].command == (
        "docker build --label description='example service' -t quoted ."
    )


def test_discover_buildable_images_skips_package_without_images(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(tmp_path, "packages/no-images", '[project]\nname = "no-images"\n')

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        images = discover_buildable_images()

    assert images == []


def test_discover_buildable_images_skips_dir_without_pyproject(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    (tmp_path / "packages" / "no-pyproject").mkdir(parents=True)

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        images = discover_buildable_images()

    assert images == []


def test_discover_buildable_images_missing_workspace_key_raises(tmp_path: Path) -> None:
    root_pyproject = tmp_path / "pyproject.toml"
    root_pyproject.write_text('[project]\nname = "root"\n')

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="tool.uv.workspace.members"):
            discover_buildable_images()


def test_discover_buildable_images_members_not_list_raises(tmp_path: Path) -> None:
    root_pyproject = tmp_path / "pyproject.toml"
    root_pyproject.write_text('[tool.uv.workspace]\nmembers = "not-a-list"\n')

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="must be a list"):
            discover_buildable_images()


def test_discover_buildable_images_empty_member_pattern_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '[""]')

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="must only contain strings"):
            discover_buildable_images()


def test_discover_buildable_images_invalid_project_table_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/bad-project",
        'project = "not-a-table"\n[tool.build.images]\nmain = "docker build ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="`project` must be a table"):
            discover_buildable_images()


def test_discover_buildable_images_missing_project_name_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/no-name",
        '[tool.build.images]\nmain = "docker build ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="project.name"):
            discover_buildable_images()


def test_discover_buildable_images_empty_project_name_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/empty-name",
        '[project]\nname = ""\n[tool.build.images]\nmain = "docker build ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="project.name"):
            discover_buildable_images()


def test_discover_buildable_images_missing_version_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/no-version",
        '[project]\nname = "no-version"\n[tool.build.images]\nmain = "docker build ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match=r"project\.version"):
            discover_buildable_images()


def test_discover_buildable_images_invalid_tool_table_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/bad-tool",
        'tool = "not-a-table"\n[project]\nname = "bad-tool"\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="`tool` must be a table"):
            discover_buildable_images()


def test_discover_buildable_images_invalid_build_table_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/bad-build",
        '[project]\nname = "bad-build"\n[tool]\nbuild = "not-a-table"\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="`tool.build` must be a table"):
            discover_buildable_images()


def test_discover_buildable_images_invalid_images_table_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["packages/*"]')
    _make_package(
        tmp_path,
        "packages/bad",
        '[project]\nname = "bad"\n[tool.build]\nimages = "not-a-table"\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="tool.build.images"):
            discover_buildable_images()


def test_discover_buildable_images_empty_image_name_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["services/*"]')
    _make_package(
        tmp_path,
        "services/empty-image",
        '[project]\nname = "empty-image"\nversion = "1.0.0"\n'
        '[tool.build.images]\n"" = "docker build ."\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="invalid `tool.build.images` entry"):
            discover_buildable_images()


def test_discover_buildable_images_non_string_command_raises(tmp_path: Path) -> None:
    root_pyproject = _make_workspace(tmp_path, '["services/*"]')
    _make_package(
        tmp_path,
        "services/bad-command",
        '[project]\nname = "bad-command"\nversion = "1.0.0"\n[tool.build.images]\nmain = {}\n',
    )

    with patch("build.REPO_ROOT", tmp_path), patch("build.ROOT_PYPROJECT", root_pyproject):
        with pytest.raises(ValueError, match="must be a string"):
            discover_buildable_images()


# --- format_image_list ---


def test_format_image_list_text(two_images: list[BuildableImage]) -> None:
    assert format_image_list(two_images, "text") == "pkg-a:main\npkg-b:gpu"


def test_format_image_list_json(two_images: list[BuildableImage], tmp_path: Path) -> None:
    with patch("build.REPO_ROOT", tmp_path):
        payload = json.loads(format_image_list(two_images, "json"))

    assert payload == [
        {
            "target": "pkg-a:main",
            "project_name": "pkg-a",
            "version": "1.2.3",
            "package_path": "packages/pkg-a",
            "image_name": "main",
            "command": "docker build -t pkg-a -f packages/pkg-a/docker/Dockerfile .",
        },
        {
            "target": "pkg-b:gpu",
            "project_name": "pkg-b",
            "version": "4.5.6",
            "package_path": "packages/pkg-b",
            "image_name": "gpu",
            "command": "docker build -t pkg-b-gpu -f packages/pkg-b/docker/Dockerfile .",
        },
    ]


def test_format_image_list_invalid_format_raises(two_images: list[BuildableImage]) -> None:
    with pytest.raises(ValueError, match="output_format"):
        format_image_list(two_images, "yaml")


# --- execute_build ---


def test_execute_build_returns_exit_code(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker build -t pkg .",
    )
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert execute_build(image) == 0


def test_execute_build_forwards_command_to_docker(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker build --build-arg FOO='bar baz' -t pkg -f Dockerfile .",
    )
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        execute_build(image)
        command: list[str] = mock_run.call_args[0][0]

    assert command == [
        "docker",
        "build",
        "--build-arg",
        "FOO=bar baz",
        "-t",
        "pkg",
        "-f",
        "Dockerfile",
        ".",
    ]


def test_execute_build_overrides_docker_tag(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker build -t pkg -f Dockerfile .",
    )
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        execute_build(image, tag="registry.example/pkg:tag")
        command: list[str] = mock_run.call_args[0][0]

    assert command == [
        "docker",
        "build",
        "-t",
        "registry.example/pkg:tag",
        "-f",
        "Dockerfile",
        ".",
    ]


def test_execute_build_pushes_after_successful_build(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker build -t pkg .",
    )
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=0)]
        assert execute_build(image, push=True) == 0

    assert mock_run.call_args_list[0][0][0] == ["docker", "build", "-t", "pkg", "."]
    assert mock_run.call_args_list[1][0][0] == ["docker", "push", "pkg"]


def test_execute_build_does_not_push_after_failed_build(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker build -t pkg .",
    )
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=2)
        assert execute_build(image, push=True) == 2

    assert mock_run.call_count == 1


def test_execute_build_rejects_tag_override_without_registered_tag(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker build .",
    )
    with pytest.raises(ValueError, match="include `-t` or `--tag`"):
        execute_build(image, tag="registry.example/pkg:tag")


def _buildx_image(tmp_path: Path) -> BuildableImage:
    return BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker buildx build -t pkg -f Dockerfile .",
    )


def test_registry_cache_ref_swaps_push_tag_for_buildcache_tag(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    ref = _registry_cache_ref("registry.example/team/pkg:main-1.0.0-abc123.mr59", image)
    assert ref == "registry.example/team/pkg:buildcache-main-1.0.0"


def test_registry_cache_ref_ignores_registry_port(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    # A registry port colon must not be mistaken for the tag separator.
    ref = _registry_cache_ref("host:5000/team/pkg:sam3-0.1.0-abc.mr59", image)
    assert ref == "host:5000/team/pkg:buildcache-main-1.0.0"


def test_registry_cache_ref_appends_arch_suffix(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    ref = _registry_cache_ref(
        "registry.example/team/pkg:main-1.0.0-abc.mr59-arm64", image, arch="arm64"
    )
    assert ref == "registry.example/team/pkg:buildcache-main-1.0.0-arm64"


@pytest.mark.parametrize(
    ("platforms", "expected"),
    [
        ("linux/arm64", "arm64"),
        ("linux/amd64", "amd64"),
        ("linux/amd64,linux/arm64", None),
        ("linux/amd64, linux/arm64", None),
        # A variant must not smuggle a slash into the cache tag.
        ("linux/arm64/v8", "arm64-v8"),
        # Malformed shapes fall back to the legacy suffixless cache ref.
        ("linux/", None),
        ("linux/arm64/v8/extra", None),
        ("arm64", None),
        # Non-tag-safe tokens must not leak into the cache tag.
        ("linux/arm 64", None),
        ("linux/arm64/v 8", None),
    ],
)
def test_single_platform_arch(platforms: str, expected: str | None) -> None:
    assert _single_platform_arch(platforms) == expected


def test_redact_build_args_masks_values_but_keeps_keys() -> None:
    command = [
        "docker",
        "buildx",
        "build",
        "--build-arg",
        "BUILDER_BASE_IMAGE=registry/base:tag",
        "--build-arg=TOKEN=s3cret",
        "--build-arg",
        "BARE",
        "-t",
        "pkg",
    ]
    assert _redact_build_args(command) == [
        "docker",
        "buildx",
        "build",
        "--build-arg",
        "BUILDER_BASE_IMAGE=***",
        "--build-arg=TOKEN=***",
        "--build-arg",
        "***",
        "-t",
        "pkg",
    ]


def test_execute_build_buildx_local_loads_single_arch(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert execute_build(image) == 0
        command: list[str] = mock_run.call_args[0][0]

    # A manifest list cannot be loaded, so a local build stays single-arch.
    assert mock_run.call_count == 1
    assert command == ["docker", "buildx", "build", "-t", "pkg", "-f", "Dockerfile", ".", "--load"]


def test_execute_build_buildx_push_builds_manifest_list(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert execute_build(image, tag="registry.example/pkg:tag", push=True) == 0
        command: list[str] = mock_run.call_args[0][0]

    # buildx pushes the manifest list itself; there is no separate docker push.
    # A stable buildcache tag lets a later build restore this run's layers.
    assert mock_run.call_count == 1
    assert command == [
        "docker",
        "buildx",
        "build",
        "-t",
        "registry.example/pkg:tag",
        "-f",
        "Dockerfile",
        ".",
        "--platform",
        "linux/amd64,linux/arm64",
        "--cache-from",
        "type=registry,ref=registry.example/pkg:buildcache-main-1.0.0",
        "--cache-to",
        "type=registry,ref=registry.example/pkg:buildcache-main-1.0.0,mode=max",
        "--push",
    ]


def test_execute_build_buildx_push_honors_platform_override(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        execute_build(image, push=True, platforms="linux/arm64")
        command: list[str] = mock_run.call_args[0][0]

    # A single-arch build gets a per-arch cache ref so the two legs never clobber.
    assert command[-7:] == [
        "--platform",
        "linux/arm64",
        "--cache-from",
        "type=registry,ref=pkg:buildcache-main-1.0.0-arm64",
        "--cache-to",
        "type=registry,ref=pkg:buildcache-main-1.0.0-arm64,mode=max",
        "--push",
    ]


def test_execute_build_buildx_push_requires_tag(tmp_path: Path) -> None:
    image = BuildableImage(
        target="pkg:main",
        project_name="pkg",
        version="1.0.0",
        package_dir=tmp_path / "packages" / "pkg",
        image_name="main",
        command="docker buildx build -f Dockerfile .",
    )
    with pytest.raises(ValueError, match="include `-t` or `--tag`"):
        execute_build(image, push=True)


def test_parse_args_collects_build_args() -> None:
    options = parse_args(["pkg-a:main", "--build-arg", "A=B", "--build-arg=C=D"])
    assert options.build_args == ("A=B", "C=D")


def test_parse_args_rejects_build_arg_without_equals() -> None:
    with pytest.raises(ValueError, match="KEY=VALUE"):
        parse_args(["pkg-a:main", "--build-arg", "NOEQUALS"])


def test_parse_args_rejects_build_arg_with_empty_key() -> None:
    # docker buildx rejects an empty build-arg name, so we do too.
    with pytest.raises(ValueError, match="KEY=VALUE"):
        parse_args(["pkg-a:main", "--build-arg", "=value"])


def test_parse_args_rejects_build_arg_with_whitespace_key() -> None:
    with pytest.raises(ValueError, match="KEY=VALUE"):
        parse_args(["pkg-a:main", "--build-arg", "   =value"])


def test_parse_args_rejects_build_arg_with_list() -> None:
    with pytest.raises(ValueError, match="--build-arg"):
        parse_args(["--list", "--build-arg", "A=B"])


def test_execute_build_appends_build_args(tmp_path: Path) -> None:
    image = _buildx_image(tmp_path)
    with patch("build.REPO_ROOT", tmp_path), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        execute_build(image, build_args=("BUILDER_BASE_IMAGE=registry/base:tag",))
        command: list[str] = mock_run.call_args[0][0]

    assert "--build-arg" in command
    assert command[command.index("--build-arg") + 1] == "BUILDER_BASE_IMAGE=registry/base:tag"


# --- main ---


def test_main_success_returns_zero(two_images: list[BuildableImage]) -> None:
    with (
        patch("build.discover_buildable_images", return_value=two_images),
        patch("build.choose_image", return_value=two_images[0]),
        patch("build.execute_build", return_value=0),
    ):
        assert main(["pkg-a:main"]) == 0


def test_main_list_json_returns_zero(two_images: list[BuildableImage], tmp_path: Path) -> None:
    with (
        patch("build.REPO_ROOT", tmp_path),
        patch("build.discover_buildable_images", return_value=two_images),
        patch("builtins.print") as mock_print,
    ):
        assert main(["--list", "--format", "json"]) == 0

    payload = json.loads(mock_print.call_args[0][0])
    assert payload[0]["target"] == "pkg-a:main"


def test_main_passes_tag_and_push_to_execute_build(two_images: list[BuildableImage]) -> None:
    with (
        patch("build.discover_buildable_images", return_value=two_images),
        patch("build.choose_image", return_value=two_images[0]),
        patch("build.execute_build", return_value=0) as mock_execute,
    ):
        assert main(["pkg-a:main", "--tag", "registry/pkg-a:tag", "--push"]) == 0

    mock_execute.assert_called_once_with(
        two_images[0],
        tag="registry/pkg-a:tag",
        push=True,
        platforms=DEFAULT_BUILD_PLATFORMS,
        build_args=(),
    )


def test_main_propagates_build_exit_code(two_images: list[BuildableImage]) -> None:
    with (
        patch("build.discover_buildable_images", return_value=two_images),
        patch("build.choose_image", return_value=two_images[0]),
        patch("build.execute_build", return_value=2),
    ):
        assert main(["pkg-a:main"]) == 2


def test_main_returns_one_on_value_error() -> None:
    with patch("build.discover_buildable_images", side_effect=ValueError("no images found")):
        assert main(["pkg-a:main"]) == 1


def test_main_returns_one_when_no_images() -> None:
    with patch("build.discover_buildable_images", return_value=[]):
        assert main(["pkg-a:main"]) == 1


def test_main_returns_130_on_keyboard_interrupt(two_images: list[BuildableImage]) -> None:
    with (
        patch("build.discover_buildable_images", return_value=two_images),
        patch("build.choose_image", side_effect=KeyboardInterrupt),
    ):
        assert main(["pkg-a:main"]) == 130


def test_module_entrypoint_exits_with_main_status() -> None:
    build_path = Path(__file__).resolve().parents[1] / "build.py"
    with (
        patch("sys.argv", ["build.py", "example-service:build"]),
        patch("subprocess.run") as mock_run,
        pytest.raises(SystemExit) as exit_info,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        runpy.run_path(str(build_path), run_name="__main__")

    assert exit_info.value.code == 0
