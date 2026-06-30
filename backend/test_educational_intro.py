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
