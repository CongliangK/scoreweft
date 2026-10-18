"""BG-D5 clip-window regression tests using real synth/FFmpeg, no sample assets.

Run without pytest: python3 -m unittest bgm_gen.tests.test_mixer_clips -v
The normal pytest suite also collects these tests in its fast tier.
"""

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

if importlib.util.find_spec("pytest") is not None:
    import pytest
    pytestmark = pytest.mark.fast

from bgm_gen.core.mixer import (_read_audio_f32, _render_track_chain,
                                _write_f32_wav)
from bgm_gen.core.project import (build_render_plan, load_project,
                                  track_engine_spec)
from bgm_gen.engines import run_engine


class TestClipWindows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="scoreweft-clips-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def project(self, name, start, end, *, sr=44100, channels=2,
                duration=8, bus=None):
        directory = self.root / name
        directory.mkdir(exist_ok=True)
        stems = directory / "stems"
        stems.mkdir(exist_ok=True)
        project = {"name": name,
                   "meta": {"spec_version": "1", "bpm": 60, "sr": sr,
                            "channels": channels, "duration_hint": duration},
                   "tracks": [{"name": "lead", "engine": "synth",
                               "instrument": "lead", "notes": [[60, 0, 6, 100]],
                               "clip": {"start_beat": start, "end_beat": end},
                               "bus": bus or []}]}
        path = directory / "project.json"
        path.write_text(json.dumps(project), encoding="utf-8")
        proj = load_project(str(path))
        return path, proj, build_render_plan(proj), stems

    def chain(self, fixture, source):
        _, proj, plan, stems = fixture
        sr, channels = proj["meta"]["sr"], proj["meta"]["channels"]
        stem = stems / "lead.synth.wav"
        _write_f32_wav(str(stem), np.asarray(source, dtype=np.float32), sr)
        before = stem.read_bytes()
        bus = _render_track_chain(proj, plan, plan["tracks"][0], 0, str(stems))
        self.assertEqual(stem.read_bytes(), before, "raw engine stem was modified")
        return _read_audio_f32(bus, sr, channels)

    def test_sustained_synth_stops_at_clip_end(self):
        for start in (0, 3, 0.12345):
            with self.subTest(start=start):
                fixture = self.project(str(start), start, start + 2)
                _, proj, plan, stems = fixture
                track = plan["tracks"][0]
                stem = stems / "lead.synth.wav"
                spec = track_engine_spec(track, proj, str(stem))
                result = run_engine(spec, runtime={"diagnostic": True})
                self.assertGreater(result["duration_s"], track["window_s"])
                source = _read_audio_f32(str(stem), 44100, 2)
                bus = _render_track_chain(proj, plan, track, 0, str(stems))
                audio = _read_audio_f32(bus, 44100, 2)
                first, last = round(start * 44100), round((start + 2) * 44100)
                expected = np.zeros((8 * 44100, 2))
                expected[first:last] = source[:last - first]
                np.testing.assert_array_equal(audio, expected)

    def test_fractional_offsets_and_ends_are_sample_accurate(self):
        for sr in (22050, 44100, 48000):
            for channels in (1, 2):
                with self.subTest(sr=sr, channels=channels):
                    start, end = 0.12345, 0.23456
                    fixture = self.project(f"{sr}-{channels}", start, end,
                                           sr=sr, channels=channels, duration=0.5)
                    source = np.full((sr, channels), 0.125, dtype=np.float32)
                    audio = self.chain(fixture, source)
                    expected = np.zeros((round(0.5 * sr), channels))
                    expected[round(start * sr):round(end * sr)] = 0.125
                    np.testing.assert_array_equal(audio, expected)

    def test_sample_rounding_uses_absolute_boundaries(self):
        # Independent endpoint rounding matters: round(5.51)-round(4.49)=2,
        # whereas round(5.51-4.49)=1. A sub-sample window may have no frames.
        for start_frame, end_frame in ((4.49, 5.51), (4.49, 4.51), (4.1, 4.4)):
            with self.subTest(start=start_frame, end=end_frame):
                fixture = self.project(f"{start_frame}-{end_frame}",
                                       start_frame / 44100, end_frame / 44100,
                                       duration=0.1)
                audio = self.chain(fixture, np.full((100, 2), 0.125))
                expected = np.zeros((4410, 2))
                expected[round(start_frame):round(end_frame)] = 0.125
                np.testing.assert_array_equal(audio, expected)

    def test_short_source_is_padded_and_not_stretched(self):
        start = 0.12345
        fixture = self.project("short", start, 0.5, duration=0.75)
        source = np.full((127, 2), 0.125)
        audio = self.chain(fixture, source)
        expected = np.zeros((33075, 2))
        first = round(start * 44100)
        expected[first:first + 127] = source
        np.testing.assert_array_equal(audio, expected)

    def test_full_length_clip_preserves_source_samples(self):
        fixture = self.project("full", 0, 0.5, duration=0.5)
        source = np.repeat(np.linspace(-0.25, 0.25, 22050,
                                       dtype=np.float32)[:, None], 2, axis=1)
        np.testing.assert_array_equal(self.chain(fixture, source), source)

    def test_fractional_project_end_is_padded_to_exact_sample_count(self):
        for sr in (8000, 22050, 44100, 48000, 96000, 192000, 384000):
            for frames in (10002.49, 10002.51, 10003.49, 10003.51):
                with self.subTest(sr=sr, frames=frames):
                    fixture = self.project(f"padding-{sr}-{frames}", 0, 2000 / sr,
                                           sr=sr, duration=frames / sr)
                    audio = self.chain(fixture, np.full((20000, 2), 0.125))
                    expected = np.zeros((round(frames), 2))
                    expected[:2000] = 0.125
                    np.testing.assert_array_equal(audio, expected)

    def test_explicit_track_effect_tail_is_preserved(self):
        sr = 44100
        fixture = self.project("echo", 0.1, 0.15, duration=0.5,
                               bus=["aecho=0.8:0.9:100:0.5"])
        audio = self.chain(fixture, np.full((sr, 2), 0.125))
        self.assertEqual(len(audio), sr // 2)
        self.assertGreater(np.max(np.abs(audio[round(0.20 * sr):round(0.24 * sr)])), 0)
        # The echo is fed only the cropped source; long source audio must not
        # leak through the dry path or keep feeding the echo after clip end.
        self.assertEqual(np.max(np.abs(audio[round(0.26 * sr):])), 0)

    def test_incremental_render_reclips_and_preserves_explicit_qc_gate(self):
        from bgm_gen.cli import main
        from bgm_gen.engines.base import measure_wav

        path, _, _, _ = self.project("incremental", 0, 4)
        output = self.root / "rendered"
        args = ["render", str(path), "-o", str(output), "-q", "--incremental"]
        # Only configuration loading is supplied for this asset-free fixture.
        # Engines, FFmpeg, mastering and QC all execute their real code paths.
        with patch("bgm_gen.engines.base.load_runtime", return_value={"diagnostic": True}), \
                patch.dict(os.environ, {"BGM_NO_PARALLEL": "1", "BGM_NO_INCREMENTAL": "0"}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
            stem = output / "stems" / "lead.synth.wav"
            original_hash = hashlib.sha256(stem.read_bytes()).hexdigest()
            original_mtime = stem.stat().st_mtime_ns
            project = json.loads(path.read_text(encoding="utf-8"))
            project["tracks"][0]["clip"]["end_beat"] = 2
            path.write_text(json.dumps(project), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as rendered:
                self.assertEqual(main(args), 0)
            self.assertFalse(json.loads(rendered.getvalue())["qc_ok"])
            self.assertEqual(stem.stat().st_mtime_ns, original_mtime)
            self.assertEqual(hashlib.sha256(stem.read_bytes()).hexdigest(), original_hash)
            premaster = _read_audio_f32(str(output / "mix_premaster.wav"), 44100, 2)
            self.assertEqual(len(premaster), 8 * 44100)
            self.assertEqual(np.count_nonzero(premaster[2 * 44100:]), 0)
            measured = measure_wav(str(output / "mix.flac"))
            self.assertEqual((measured["duration_s"], measured["sr"], measured["channels"]),
                             (8.0, 44100, 2))
            with redirect_stdout(io.StringIO()) as checked:
                self.assertEqual(main(["qc", str(output / "mix.flac"),
                                       "--project", str(path)]), 1)
            self.assertFalse(json.loads(checked.getvalue())["items"]["silent_window"]["pass"])


if __name__ == "__main__":
    unittest.main()
