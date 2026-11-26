# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Import shims that let the upstream SeedVR scripts load on the service's base image."""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from typing import NoReturn

TORCHVISION_VIDEO_MODULE = "torchvision.io.video"


def _video_io_unavailable(*_args: object, **_kwargs: object) -> NoReturn:
    raise RuntimeError(
        f"{TORCHVISION_VIDEO_MODULE} is unavailable in this TorchVision build; "
        "decode video through core.media."
    )


def install_torchvision_video_fallback() -> bool:
    """Stand in for ``torchvision.io.video`` when this TorchVision build cannot import it.

    The upstream SeedVR variant scripts import ``read_video`` from it at module load
    but only call it in their own CLI loop, which the service does not use: frames
    are decoded through ``core.media``. The NGC PyTorch 26.07 TorchVision ships the
    module as a re-export of an unavailable internal package, so the import itself
    fails. The stand-in's functions raise if anything calls them.

    Returns True when the stand-in was installed, False when the real module imports.
    """
    try:
        importlib.import_module(TORCHVISION_VIDEO_MODULE)
        return False
    except ImportError:
        sys.modules.pop(TORCHVISION_VIDEO_MODULE, None)

    module = types.ModuleType(TORCHVISION_VIDEO_MODULE)
    module.__spec__ = importlib.util.spec_from_loader(TORCHVISION_VIDEO_MODULE, loader=None)
    for name in ("read_video", "read_video_timestamps", "write_video"):
        module.__dict__[name] = _video_io_unavailable
    sys.modules[TORCHVISION_VIDEO_MODULE] = module
    return True
