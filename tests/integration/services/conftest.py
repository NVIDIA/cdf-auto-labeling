# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for deterministic service CLI integration tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from service_harness import RunService, build_completed_scene, build_service_runner


@pytest.fixture(scope="session")
def run_service() -> RunService:
    return build_service_runner()


@pytest.fixture
def completed_scene() -> Callable[..., Path]:
    return build_completed_scene
