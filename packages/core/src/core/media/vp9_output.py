# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Backward-compatible imports for the VP9 output utilities."""

from core.media.video_output import (
    VP9_ENCODER_OPTIONS,
    Vp9VideoWriter,
    configure_vp9_output_stream,
)

__all__ = ["VP9_ENCODER_OPTIONS", "Vp9VideoWriter", "configure_vp9_output_stream"]
