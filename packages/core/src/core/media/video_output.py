# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Shared video encoding; H.264 is opt-in for temporary inference payloads."""

from __future__ import annotations

import importlib
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal

VideoCodec = Literal["vp9", "h264"]

_AVCOL_RANGE_MPEG = 1
_AVCOL_PRI_BT709 = 1
_AVCOL_TRC_BT709 = 1
_AVCOL_SPC_BT709 = 1

VP9_ENCODER_OPTIONS: dict[str, str] = {
    "crf": "15",
    "deadline": "good",
    "cpu-used": "2",
    "row-mt": "1",
    "aq-mode": "1",
}


def configure_vp9_output_stream(stream: Any, *, width: int, height: int) -> None:
    """Configure a libvpx-vp9 stream with the workspace output policy."""
    stream.width = width
    stream.height = height
    stream.pix_fmt = "yuv420p"
    stream.options = dict(VP9_ENCODER_OPTIONS)
    codec_context = stream.codec_context
    codec_context.color_range = _AVCOL_RANGE_MPEG
    codec_context.color_primaries = _AVCOL_PRI_BT709
    codec_context.color_trc = _AVCOL_TRC_BT709
    codec_context.colorspace = _AVCOL_SPC_BT709


class VideoWriter:
    """Encode frames once using VP9 by default or explicitly requested H.264."""

    def __init__(
        self,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: float,
        frame_format: str = "bgr24",
        codec: VideoCodec = "vp9",
    ) -> None:
        if codec not in ("vp9", "h264"):
            raise ValueError(f"Unsupported video output codec: {codec}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._av = _import_av()
        if codec == "h264" and "libx264" not in self._av.codecs_available:
            raise RuntimeError("H.264 inference encoding requires PyAV built with libx264.")
        self._frame_format = frame_format
        self._container = self._av.open(str(output_path), mode="w")
        self._closed = False
        try:
            self._stream = self._container.add_stream(
                "libvpx-vp9" if codec == "vp9" else "libx264",
                rate=Fraction(fps).limit_denominator(1000),
            )
            if codec == "vp9":
                configure_vp9_output_stream(self._stream, width=width, height=height)
            else:
                self._stream.width = width + width % 2
                self._stream.height = height + height % 2
                self._stream.pix_fmt = "yuv420p"
                self._stream.options = {"crf": "18", "preset": "fast"}
        except Exception:
            self._container.close()
            self._closed = True
            raise

    def write(self, frame: Any) -> None:
        """Encode and mux one ndarray frame."""
        if self._closed:
            raise RuntimeError("Cannot write to a closed video writer.")
        video_frame = self._av.VideoFrame.from_ndarray(frame, format=self._frame_format)
        for packet in self._stream.encode(video_frame):
            self._container.mux(packet)

    def close(self) -> None:
        """Flush the encoder and close the output container."""
        if self._closed:
            return
        try:
            for packet in self._stream.encode(None):
                self._container.mux(packet)
        finally:
            self._container.close()
            self._closed = True

    def __enter__(self) -> VideoWriter:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()


class Vp9VideoWriter(VideoWriter):
    """Preserve the VP9-only writer interface for persisted annotation videos."""

    def __init__(
        self,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: float,
        frame_format: str = "bgr24",
    ) -> None:
        super().__init__(
            output_path, width=width, height=height, fps=fps, frame_format=frame_format, codec="vp9"
        )


def _import_av() -> Any:
    try:
        return importlib.import_module("av")
    except ImportError as exc:
        raise RuntimeError("Video encoding requires the optional PyAV package.") from exc


__all__ = [
    "VideoCodec",
    "VideoWriter",
    "VP9_ENCODER_OPTIONS",
    "Vp9VideoWriter",
    "configure_vp9_output_stream",
]
