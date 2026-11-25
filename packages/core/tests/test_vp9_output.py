# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest
from core.media import VP9_ENCODER_OPTIONS, VideoWriter, configure_vp9_output_stream


def test_configure_vp9_output_stream_sets_quality_and_color_metadata() -> None:
    class FakeCodecContext:
        color_range = 0
        color_primaries = 0
        color_trc = 0
        colorspace = 0

    class FakeStream:
        width = 0
        height = 0
        pix_fmt = ""

        def __init__(self) -> None:
            self.options: dict[str, str] = {}
            self.codec_context = FakeCodecContext()

    stream = FakeStream()

    configure_vp9_output_stream(stream, width=1280, height=720)

    assert stream.width == 1280
    assert stream.height == 720
    assert stream.pix_fmt == "yuv420p"
    assert stream.options == VP9_ENCODER_OPTIONS
    assert stream.options is not VP9_ENCODER_OPTIONS
    assert stream.codec_context.color_range == 1
    assert stream.codec_context.color_primaries == 1
    assert stream.codec_context.color_trc == 1
    assert stream.codec_context.colorspace == 1


@pytest.mark.parametrize("codec", ["vp9", "h264"])
def test_video_writer_encodes_selected_codec_once(tmp_path: Path, codec: str) -> None:
    av = pytest.importorskip("av")
    np = pytest.importorskip("numpy")
    if codec == "h264" and "libx264" not in av.codecs_available:
        pytest.skip("Optional H.264 inference encoder is not installed")

    output = tmp_path / "window.mp4"
    with VideoWriter(output, width=32, height=24, fps=10.0, codec=codec) as writer:
        for value in range(10):
            writer.write(np.full((24, 32, 3), value * 20, dtype=np.uint8))
    with av.open(str(output)) as container:
        assert container.streams.video[0].codec_context.name == codec
        frames = list(container.decode(video=0))
        assert len(frames) == 10
        assert [float(frame.time) for frame in frames] == pytest.approx([i / 10 for i in range(10)])
        assert [(frame.width, frame.height) for frame in frames] == [(32, 24)] * 10


def test_missing_h264_encoder_fails_explicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    av = pytest.importorskip("av")
    monkeypatch.setattr(av, "codecs_available", av.codecs_available - {"libx264"})
    with pytest.raises(RuntimeError, match="requires PyAV built with libx264"):
        VideoWriter(tmp_path / "window.mp4", width=32, height=24, fps=10.0, codec="h264")
    assert not (tmp_path / "window.mp4").exists()
