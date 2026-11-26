# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib
import sys
import types

import pytest
from super_resolution import seedvr2_compat
from super_resolution.seedvr2_compat import (
    TORCHVISION_VIDEO_MODULE,
    install_torchvision_video_fallback,
)


def test_keeps_a_working_torchvision_video_module(monkeypatch: pytest.MonkeyPatch) -> None:
    real = types.ModuleType(TORCHVISION_VIDEO_MODULE)
    monkeypatch.setitem(sys.modules, TORCHVISION_VIDEO_MODULE, real)

    assert install_torchvision_video_fallback() is False
    assert sys.modules[TORCHVISION_VIDEO_MODULE] is real


def test_stands_in_when_the_import_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, TORCHVISION_VIDEO_MODULE, raising=False)
    real_import = importlib.import_module

    def failing_import(name: str, package: str | None = None) -> types.ModuleType:
        if name == TORCHVISION_VIDEO_MODULE:
            raise ModuleNotFoundError("No module named 'pytorch'")
        return real_import(name, package)

    monkeypatch.setattr(seedvr2_compat.importlib, "import_module", failing_import)

    assert install_torchvision_video_fallback() is True
    # The upstream SeedVR scripts' import line now succeeds...
    from torchvision.io.video import read_video  # noqa: PLC0415

    # ...and any call fails loudly instead of decoding outside core.media.
    with pytest.raises(RuntimeError, match="core.media"):
        read_video("clip.mp4")
    monkeypatch.delitem(sys.modules, TORCHVISION_VIDEO_MODULE)
