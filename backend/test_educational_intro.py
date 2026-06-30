import sys, types, warnings
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")


def test_start_video_generation_uses_resolution_override(monkeypatch):
    """When a resolution is passed, it must be sent in the request payload."""
    import app.services.sora_service as ss

    captured = {}

    def fake_post(url, headers=None, json=None, verify=None, timeout=None):
        captured["resolution"] = json["Resolution"]
        resp = types.SimpleNamespace()
        resp.status_code = 200
        resp.json = lambda: {"response": [{"videostoreid": "vid-123"}]}
        resp.text = ""
        return resp

    monkeypatch.setattr(ss, "_get_sora_token", lambda: ("tok", {"Authorization": "Bearer tok"}))
    monkeypatch.setattr(ss, "_get_env_secret", lambda name: "x")
    monkeypatch.setattr(ss.requests, "post", fake_post)

    vid = ss.start_video_generation("a prompt", resolution="1280x720")
    assert vid == "vid-123"
    assert captured["resolution"] == "1280x720"


def test_build_intro_prompt_mentions_topic_and_bans_text():
    from app.services.educational_intro import build_intro_prompt
    p = build_intro_prompt("RAG Learning for Beginners")
    assert "RAG Learning for Beginners" in p
    assert "No on-screen text" in p
    assert "16:9" in p


def test_build_agenda_lines_splits_into_two_lines():
    from app.services.educational_intro import build_agenda_lines
    titles = ["What is RAG?", "Why RAG Matters", "Architecture", "Code Example",
              "Tools & Ecosystem", "Learning Path"]
    lines = build_agenda_lines(titles, max_lines=2)
    assert len(lines) == 2
    assert "What is RAG?" in lines[0]
    assert "Learning Path" in lines[1]
    assert "  •  " in lines[0]   # bullet separator


def test_build_agenda_lines_empty():
    from app.services.educational_intro import build_agenda_lines
    assert build_agenda_lines([]) == []
    assert build_agenda_lines(["", "   "]) == []


import os, subprocess


def _make_synthetic_clip(path, seconds=2, size="1280x720"):
    """Create a tiny silent test clip with FFmpeg lavfi."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=navy:s={size}:d={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=440:d={seconds}",
         "-shortest", "-pix_fmt", "yuv420p", path],
        capture_output=True, check=True,
    )


def _probe_wh(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    w, h = out.split(",")
    return int(w), int(h)


def test_overlay_title_produces_1080p(tmp_path):
    from app.services.educational_intro import _overlay_title
    raw = str(tmp_path / "raw.mp4")
    out = str(tmp_path / "titled.mp4")
    _make_synthetic_clip(raw)
    _overlay_title(raw, "RAG Learning for Beginners",
                   ["What is RAG?  •  Why RAG Matters", "Code Example  •  Tools"], out)
    assert os.path.exists(out)
    assert _probe_wh(out) == (1920, 1080)


def _probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def test_concat_intro_joins_durations(tmp_path):
    from app.services.educational_intro import concat_intro
    intro = str(tmp_path / "intro.mp4")
    lesson = str(tmp_path / "lesson.mp4")
    out = str(tmp_path / "final.mp4")
    _make_synthetic_clip(intro, seconds=2, size="1920x1080")
    _make_synthetic_clip(lesson, seconds=3, size="1920x1080")
    concat_intro(intro, lesson, out)
    assert _probe_wh(out) == (1920, 1080)
    # ~5s total (allow tolerance for re-encode boundaries)
    assert 4.0 <= _probe_duration(out) <= 6.0
