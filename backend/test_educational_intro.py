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
