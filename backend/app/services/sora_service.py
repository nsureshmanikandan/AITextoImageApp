"""
Sora-2 video generation service for VernacularCast Brand Ads.
Generates an optimised Sora-2 prompt via GPT-4o, then attempts video
submission.  The API call will fail without the platform gateway secrets —
that is expected; the UI will show the generated prompt even when the
video cannot be submitted.
"""
import logging
import time
import base64
import os
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

VIDEO_TYPES = {
    "patient_journey": {
        "label": "Patient Journey Ad (Emotional Story)",
        "direction": (
            "Tell a compressed emotional patient story: open on a worried face, "
            "transition to a hopeful doctor consultation, end with the patient "
            "smiling in daily life. Warm color grading, soft lighting, gentle camera movement."
        ),
    },
    "doctor_authority": {
        "label": "Doctor Authority Ad (Trust & Credibility)",
        "direction": (
            "Feature a confident doctor in a clean clinical setting speaking directly "
            "to camera. Professional lighting, steady mid-shot, subtle medical environment "
            "in background. Convey trust and expertise."
        ),
    },
    "scientific_mechanism": {
        "label": "Scientific Mechanism Ad (Molecular / CGI)",
        "direction": (
            "Show a stylized CGI molecular animation of the product's mechanism of action. "
            "Start zoomed into cellular/product level, pull out to show a positive response. "
            "Clean blues and whites, modern aesthetic."
        ),
    },
    "lifestyle_outcome": {
        "label": "Lifestyle Outcome Ad (Post-Treatment Life)",
        "direction": (
            "Show customers enjoying everyday life with the product — outdoors, family, active. "
            "Bright natural lighting, warm tones, uplifting energy. Focus on freedom and normalcy."
        ),
    },
    "awareness_campaign": {
        "label": "Awareness Campaign Ad (Educational)",
        "direction": (
            "Create an educational awareness piece: open with key statistics or symptoms as text "
            "overlays, transition to a reassuring expert, end with a clear call-to-action. "
            "Clean typography, informative pacing."
        ),
    },
    "brand_story": {
        "label": "Brand Story Ad (Heritage & Trust)",
        "direction": (
            "Weave a brief brand heritage story: archival-style opening, modern product shot, "
            "close on a customer satisfaction moment. Nostalgic warmth transitioning to "
            "contemporary confidence."
        ),
    },
}


SORA_SYSTEM_PROMPT = """You are an expert video prompt engineer for the Sora-2 AI video generation model.
Produce a SINGLE, self-contained text prompt for a COMPLETE 12-second brand marketing video ad.

CRITICAL — 12-SECOND COMPLETENESS RULE:
The video is exactly 12 seconds. The ad must feel FINISHED at second 12 — not cut off, not rushed.

TIMING STRUCTURE:
- Seconds 0-3: OPENING — establish scene, mood, hook. Music fades in. Voiceover: ONE line (max 8 words).
- Seconds 4-8: CORE MESSAGE — main visual storytelling. Voiceover: ONE key sentence (max 12 words). Music mid-energy.
- Seconds 9-12: CLOSE — brand name on screen, music resolves, voiceover closing tagline/CTA (max 6 words). Final frame holds ~1 second.

AUDIO RULES:
- Total voiceover: MAX 3 sentences, MAX 26 words total across 12 seconds.
- Music: soft start → gentle build → clean resolve. No abrupt cuts.

VISUAL RULES:
- MAX 3 scene changes. Use smooth transitions (dissolve, slow pan).
- Final 2 seconds: brand name clearly on screen.

OUTPUT: ONLY the Sora-2 prompt text. No explanations, no markdown. Under 250 words.
Include brand name, product, key message, camera angles, lighting, mood, transitions."""


def _get_gpt5_sso_token() -> str:
    """Get OAuth2 token for GPT-5 gateway using SSO client credentials (direct POST, no azure-identity)."""
    resp = requests.post(
        _get_env_secret("SORA_GPT_SSO_URL"),
        data={
            "grant_type":    "client_credentials",
            "client_id":     _get_env_secret("SORA_GPT_CLIENT_ID"),
            "client_secret": _get_env_secret("SORA_GPT_CLIENT_SECRET"),
            "scope":         _get_env_secret("SORA_GPT_SCOPE"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=False,
        timeout=15,
    )
    if resp.status_code != 200:
        raise ValueError(f"GPT-5 SSO token error {resp.status_code}: {resp.text[:300]}")
    token = resp.json().get("access_token", "")
    if not token:
        raise ValueError("GPT-5 SSO token response missing access_token")
    logger.info("GPT-5 SSO token obtained successfully")
    return token


def _call_gpt5_chat(messages: list, temperature: float = 0.7, max_tokens: int = 400) -> str:
    """Call GPT-5 via Accenture gateway REST API directly."""
    token      = _get_gpt5_sso_token()
    base_url   = _get_env_secret("SORA_GPT_BASE_URL")
    client_id  = _get_env_secret("SORA_GPT_VISION_CLIENT_ID")
    engine_id  = _get_env_secret("SORA_GPT_ENGINE_ID")
    model_id   = _get_env_secret("SORA_GPT_MODEL_ID")
    x_auth     = _get_env_secret("SORA_GPT_XAUTH")
    x_user     = _get_env_secret("SORA_GPT_USER_ID")

    url = f"{base_url}/Client/{client_id}/Engine/{engine_id}/Model/{model_id}/ChatCompletion"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Authcode":    x_auth,
            "X-UserId":      x_user,
            "Content-Type":  "application/json",
        },
        json={
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        },
        verify=False,
        timeout=60,
    )
    if resp.status_code != 200:
        raise ValueError(f"GPT-5 chat error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    # Gateway may wrap in {"response": [...]} or return standard OpenAI shape
    if "choices" in data:
        return (data["choices"][0].get("message", {}).get("content") or "").strip()
    items = data.get("response") or []
    if items and isinstance(items[0], dict):
        return (items[0].get("content") or items[0].get("message", {}).get("content") or "").strip()
    raise ValueError(f"Unexpected GPT-5 response shape: {str(data)[:300]}")


async def build_sora_prompt(
    brand_name: str,
    product: str,
    key_message: str,
    target_audience: str,
    cta: str,
    tone: str,
    video_type: str | None = None,
) -> str:
    """Generate a Sora-2 video prompt using Azure OpenAI GPT-4o (already configured in VernacularCast)."""
    from openai import AsyncAzureOpenAI

    vt_block = ""
    if video_type and video_type in VIDEO_TYPES:
        vt = VIDEO_TYPES[video_type]
        vt_block = f"\nVIDEO STYLE: {vt['label']}\nSTYLE DIRECTION: {vt['direction']}\n"
    else:
        vt_block = "\nVIDEO STYLE: Choose the most appropriate style for this brand and tone.\n"

    user = (
        f"BRAND: {brand_name}\n"
        f"PRODUCT / CAMPAIGN: {product}\n"
        f"TARGET AUDIENCE: {target_audience}\n"
        f"KEY MESSAGE: {key_message}\n"
        f"CALL TO ACTION: {cta}\n"
        f"TONE: {tone}\n"
        f"{vt_block}\n"
        "CONSTRAINTS:\n"
        "- EXACTLY 12 seconds. Feels COMPLETE at second 12.\n"
        "- Structure: 0-3s opening hook, 4-8s core message, 9-12s brand close with logo.\n"
        "- Voiceover: MAX 3 sentences, MAX 26 words total. Finishes by second 11.\n"
        "- Music: soft start -> build -> clean resolve at second 12.\n"
        "- Visuals: MAX 3 scenes with smooth transitions. Final 2s = brand name on screen.\n"
    )

    def _get_az(name: str, default: str = "") -> str:
        try:
            return _get_env_secret(name)
        except Exception:
            return os.getenv(name, default)

    endpoint   = _get_az("AZURE_OPENAI_ENDPOINT")
    api_key    = _get_az("AZURE_OPENAI_KEY") or _get_az("AZURE_OPENAI_API_KEY")
    deployment = _get_az("AZURE_OPENAI_DEPLOYMENT") or "gpt-4o"
    api_ver    = _get_az("AZURE_OPENAI_API_VERSION") or "2024-12-01-preview"

    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_ver,
    )
    resp = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SORA_SYSTEM_PROMPT},
            {"role": "user",   "content": user},
        ],
        temperature=0.7,
        max_tokens=400,
    )
    prompt = (resp.choices[0].message.content or "").strip()
    logger.info("Sora-2 prompt generated via GPT-4o (%d chars)", len(prompt))
    return prompt


def _get_env_secret(name: str) -> str:
    """Read Sora gateway credentials from .env (same source as app config)."""
    from pathlib import Path
    from dotenv import dotenv_values
    _root = Path(__file__).resolve().parents[4]   # repo root
    _back = Path(__file__).resolve().parents[3]   # backend/
    _env  = {**dotenv_values(_root / ".env"), **dotenv_values(_back / ".env")}
    val   = _env.get(name) or os.getenv(name, "")
    if not val:
        raise ValueError(f"Missing Sora credential: {name}")
    return val


_SAFE_RESOLUTION = "720x1280"   # always supported by base sora-2 model


def start_video_generation(prompt: str) -> str:
    """
    Submit a video generation job to the Sora-2 API gateway.
    Returns videostoreid on success.
    Raises ValueError if credentials are not configured.

    Resolution/duration are configurable via .env (SORA_RESOLUTION, SORA_DURATION).
    Base sora-2 supports 720x1280 / 1280x720. HD sizes (1024x1792 / 1792x1024)
    require a sora-2-pro deployment — set SORA_MODEL_ID to the pro model and
    SORA_RESOLUTION=1024x1792. If the gateway rejects the configured resolution,
    we log the error and auto-retry once at the safe 720x1280 so the job survives.
    """
    _, headers = _get_sora_token()
    url = (
        f"{_get_env_secret('SORA_BASE_URL')}"
        f"/Client/{_get_env_secret('SORA_CLIENT_ID')}"
        f"/Engine/{_get_env_secret('SORA_ENGINE_ID')}"
        f"/Model/{_get_env_secret('SORA_MODEL_ID')}"
        f"/VideoGeneration"
    )
    resolution = _try_env("SORA_RESOLUTION", _SAFE_RESOLUTION)
    duration   = _try_env("SORA_DURATION", "12")

    def _submit(res: str):
        return requests.post(
            url,
            headers=headers,
            json={"callbackurl": "", "prompt": prompt, "Resolution": res, "Duration": duration},
            verify=False,
            timeout=30,
        )

    gen_resp = _submit(resolution)

    # Graceful fallback: if a non-default resolution is rejected, retry at the safe size.
    if gen_resp.status_code != 200 and resolution != _SAFE_RESOLUTION:
        logger.warning(
            "Sora rejected resolution %s (%d: %s) — retrying at %s",
            resolution, gen_resp.status_code, gen_resp.text[:200], _SAFE_RESOLUTION,
        )
        gen_resp = _submit(_SAFE_RESOLUTION)

    if gen_resp.status_code != 200:
        raise ValueError(f"Sora generation error {gen_resp.status_code}: {gen_resp.text[:200]}")

    data = gen_resp.json()
    vid_id = (data.get("response") or [{}])[0].get("videostoreid", "")
    if not vid_id:
        raise ValueError(f"No videostoreid in Sora response: {data}")
    logger.info("Sora-2 job submitted at %s (%ss): %s", resolution, duration, vid_id)
    return vid_id


def _get_sora_token() -> tuple[str, dict]:
    """Get Sora bearer token + common headers. Returns (token, base_headers)."""
    token_url      = _get_env_secret("SORA_TOKEN_URL")
    client_id_tok  = _get_env_secret("SORA_TOKEN_CLIENT_ID")
    client_sec_tok = _get_env_secret("SORA_TOKEN_CLIENT_SECRET")
    token_scope    = _get_env_secret("SORA_TOKEN_SCOPE")
    token_cookie   = _try_env("SORA_TOKEN_COOKIE", "")

    tok_resp = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cookie": token_cookie},
        data=(
            f"grant_type=client_credentials"
            f"&client_id={client_id_tok}"
            f"&client_secret={client_sec_tok}"
            f"&scope={token_scope}"
        ),
        verify=False,
        timeout=15,
    )
    if tok_resp.status_code != 200:
        raise ValueError(f"Sora token error {tok_resp.status_code}: {tok_resp.text[:200]}")
    token = tok_resp.json().get("access_token", "")
    if not token:
        raise ValueError("Sora token response missing access_token")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Authcode": _get_env_secret("SORA_XAUTH"),
        "X-UserId":   _get_env_secret("SORA_USER_ID"),
        "Content-Type": "application/json",
    }
    return token, headers


def _try_env(name: str, default: str = "") -> str:
    try:
        return _get_env_secret(name)
    except Exception:
        return os.getenv(name, default)


def poll_sora_video(videostoreid: str) -> dict:
    """
    Poll Sora gateway using GetVideo endpoint.
    Returns {"ready": True, "base64": "<b64>"} when done, {"ready": False} when still rendering.
    """
    import base64 as _b64
    _, headers = _get_sora_token()
    base_url  = _get_env_secret("SORA_BASE_URL")
    sora_cid  = _get_env_secret("SORA_CLIENT_ID")
    engine_id = _get_env_secret("SORA_ENGINE_ID")
    model_id  = _get_env_secret("SORA_MODEL_ID")
    url = f"{base_url}/Client/{sora_cid}/Engine/{engine_id}/Model/{model_id}/GetVideo/{videostoreid}"

    resp = requests.get(url, headers=headers, verify=False, timeout=30)
    if resp.status_code != 200:
        logger.debug("GetVideo %s → %d", videostoreid, resp.status_code)
        return {"ready": False}

    items = resp.json().get("response") or []
    if items and isinstance(items[0], dict):
        b64 = items[0].get("base64string", "")
        if b64:
            return {"ready": True, "base64": b64}
    return {"ready": False}


def download_sora_video(videostoreid: str, save_path: str,
                        poll_interval: int = 10, timeout: int = 400) -> str:
    """
    Poll until Sora video is ready, then decode base64 and save to save_path.
    Returns save_path on success, raises TimeoutError if not ready within timeout seconds.
    """
    import base64 as _b64
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        result = poll_sora_video(videostoreid)
        if result["ready"]:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(_b64.b64decode(result["base64"]))
            logger.info("Sora video saved: %s", save_path)
            return save_path
        logger.info("Sora video not ready yet, retrying in %ds…", poll_interval)
        time.sleep(poll_interval)

    raise TimeoutError(f"Sora video {videostoreid} not ready within {timeout}s")
