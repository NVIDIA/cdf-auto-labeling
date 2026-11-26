# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tracker factory.

Thin wrapper around :class:`core.registry.Registry`. Concrete backends
self-register via :func:`register_tracker` (typically from a
``backends/*.py`` module that is imported at package import time).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from importlib.metadata import entry_points

from core.registry import Registry

from detection_and_tracking.config import DetectionAndTrackingConfig
from detection_and_tracking.tracker import Tracker

TrackerKind = str
PLANNED_TRACKER_KINDS: frozenset[str] = frozenset(
    {
        "rfdetr-boosttrack",
        "rfdetr-deepocsort",
        "rfdetr-bytetrack",
        "sam3",
    }
)

TrackerBuilder = Callable[[logging.Logger, DetectionAndTrackingConfig], Tracker]

_REGISTRY: Registry[Tracker] = Registry("tracker kind")


def register_tracker(kind: str, builder: TrackerBuilder) -> None:
    """Register a tracker builder under ``kind``.

    Re-registering the same kind silently overwrites the previous entry
    so tests and plug-ins can replace builders without teardown.
    """
    _REGISTRY.register(kind, builder)


def create_tracker(
    kind: TrackerKind | str,
    logger: logging.Logger,
    config: DetectionAndTrackingConfig | None = None,
) -> Tracker:
    """Construct a registered tracker instance.

    Raises ``NotImplementedError`` for planned backends whose real
    implementation has not landed yet, and ``ValueError`` for unknown
    kinds.
    """
    if kind in PLANNED_TRACKER_KINDS and not _REGISTRY.is_registered(kind):
        registered = ", ".join(_REGISTRY.list()) or "<none>"
        raise NotImplementedError(
            f"Tracker backend {kind!r} is planned but not implemented in this scaffold. "
            f"Registered tracker backends: {registered}. Select a registered backend until "
            "the requested backend migration lands."
        )
    if config is None:
        if not _REGISTRY.is_registered(kind):
            return _REGISTRY.create(kind, logger, DetectionAndTrackingConfig())
        config = DetectionAndTrackingConfig(tracker=kind)
    return _REGISTRY.create(kind, logger, config)


TRACKER_ENTRY_POINT_GROUP = "cdf.trackers"


def load_entry_point_trackers(
    logger: logging.Logger, group: str = TRACKER_ENTRY_POINT_GROUP
) -> list[str]:
    """Register tracker builders published by installed packages.

    Each entry point's name is the tracker kind and its object is a
    ``TrackerBuilder``, for example in a plug-in's ``pyproject.toml``::

        [project.entry-points."cdf.trackers"]
        my-detector = "my_package.tracker:build_tracker"

    A plug-in that fails to load is logged and skipped so it cannot break
    the built-in backends.

    Returns:
        The tracker kinds registered from entry points.
    """
    loaded: list[str] = []
    for entry_point in entry_points(group=group):
        try:
            builder = entry_point.load()
            if not callable(builder):
                raise TypeError("tracker factory is not callable")
        except Exception as exc:
            logger.warning(
                "Skipping tracker plug-in %r (%s): %s", entry_point.name, entry_point.value, exc
            )
            continue
        register_tracker(entry_point.name, builder)
        loaded.append(entry_point.name)
    return loaded


def list_trackers() -> list[str]:
    """Return the sorted list of registered tracker kinds."""
    return _REGISTRY.list()


__all__ = [
    "TrackerBuilder",
    "TrackerKind",
    "PLANNED_TRACKER_KINDS",
    "TRACKER_ENTRY_POINT_GROUP",
    "create_tracker",
    "list_trackers",
    "load_entry_point_trackers",
    "register_tracker",
]
