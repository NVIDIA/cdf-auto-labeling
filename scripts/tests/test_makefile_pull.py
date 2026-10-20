# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the ``make pull`` target in the repository Makefile."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from build import _find_build_tag, discover_buildable_images

REPO_ROOT = Path(__file__).resolve().parents[2]
UNPUBLISHED_IMAGES = {"cdf-example-service"}

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="GNU Make is not installed")


def _make_pull(*overrides: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", "-s", "pull", "CONTAINER_RUNTIME=echo", *overrides],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_variable(name: str) -> str:
    completed = subprocess.run(
        ["make", "--no-print-directory", "-s", "-f", "Makefile", "-f", "-", "print"],
        cwd=REPO_ROOT,
        input=f"print:\n\t@echo $({name})\n",
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _pulled_images(stdout: str) -> list[str]:
    prefix = "Pulling "
    return [line.removeprefix(prefix) for line in stdout.splitlines() if line.startswith(prefix)]


def test_pull_pulls_and_tags_every_default_image() -> None:
    result = _make_pull()

    assert result.returncode == 0, result.stderr
    images = _make_variable("NGC_IMAGES").split()
    assert len(images) == 12
    for image in images:
        ref = f"nvcr.io/nvidia/{image}:1.1.0"
        assert f"Pulling {ref}" in result.stdout
        assert f"pull {ref}" in result.stdout
        assert f"tag {ref} {image}" in result.stdout


def test_pull_defaults_cover_every_published_registered_image() -> None:
    registered = {
        tag
        for image in discover_buildable_images()
        if (tag := _find_build_tag(shlex.split(image.command))) and tag.startswith("cdf-")
    }

    assert set(_make_variable("NGC_IMAGES").split()) == registered - UNPUBLISHED_IMAGES


def test_pull_default_tag_matches_project_version() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        version = tomllib.load(pyproject_file)["project"]["version"]

    assert _make_variable("NGC_TAG") == version


def test_pull_honors_image_subset_tag_and_registry_overrides() -> None:
    result = _make_pull(
        "NGC_IMAGES=cdf-captioning-service cdf-visual-qa-service",
        "NGC_TAG=2.0.0",
        "NGC_REGISTRY=registry.example/team",
    )

    assert result.returncode == 0, result.stderr
    assert _pulled_images(result.stdout) == [
        "registry.example/team/cdf-captioning-service:2.0.0",
        "registry.example/team/cdf-visual-qa-service:2.0.0",
    ]
    assert "tag registry.example/team/cdf-visual-qa-service:2.0.0 cdf-visual-qa-service" in (
        result.stdout
    )


def test_pull_stops_at_the_first_failed_pull() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-s",
            "pull",
            "CONTAINER_RUNTIME=false",
            "NGC_IMAGES=cdf-captioning-service cdf-visual-qa-service",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert _pulled_images(result.stdout) == ["nvcr.io/nvidia/cdf-captioning-service:1.1.0"]


def test_pull_with_empty_image_list_does_nothing() -> None:
    result = _make_pull("NGC_IMAGES=")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
