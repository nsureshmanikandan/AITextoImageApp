"""Quick Sora-2 test -- run from backend/ directory: python test_sora.py"""
import asyncio
import sys
sys.path.insert(0, ".")

from app.services.sora_service import _get_gpt5_sso_token, _call_gpt5_chat, _get_env_secret, start_video_generation

TEST_PROMPT = (
    "A 12-second pharmaceutical awareness ad for TREMFYA. "
    "Seconds 0-3: a man sitting at his desk clutching his stomach, warm office light, soft music fades in, "
    "voiceover: 'Persistent stomach pain? It could be IBD.' "
    "Seconds 4-8: dissolve to a calm doctor-patient consultation in a bright clinic, "
    "voiceover: 'TREMFYA offers a new path forward for IBD patients.' "
    "Seconds 9-12: slow fade to white background, TREMFYA logo appears centred, "
    "music resolves gently, voiceover: 'Talk to your doctor today.' Final frame holds 1 second."
)

def test_gpt5_auth():
    print("\n-- Step 1: GPT-5 SSO token + chat ------------------")
    try:
        token = _get_gpt5_sso_token()
        print(f"  OK SSO token obtained ({len(token)} chars)")
        reply = _call_gpt5_chat([{"role": "user", "content": "Reply with exactly: Sora test OK"}], max_tokens=10)
        print(f"  OK GPT-5 response: {reply}")
        return True
    except Exception as e:
        print(f"  FAIL GPT-5 auth/chat failed: {e}")
        return False

def test_sora_submit():
    print("\n-- Step 2: Sora-2 video submission ------------------")
    try:
        vid_id = start_video_generation(TEST_PROMPT)
        print(f"  OK Submitted! videostoreid: {vid_id}")
        return vid_id
    except Exception as e:
        print(f"  FAIL Submission failed: {e}")
        return None

async def test_prompt_gen():
    print("\n-- Step 3: Full GPT-5 Sora prompt generation -------")
    from app.services.sora_service import build_sora_prompt
    try:
        prompt = await build_sora_prompt(
            brand_name="TREMFYA",
            product="TREMFYA for IBD -- Awareness Campaign",
            key_message="Persistent stomach pain could be IBD. TREMFYA can help.",
            target_audience="US patients with undiagnosed IBD",
            cta="Talk to your doctor about TREMFYA",
            tone="emotional",
        )
        print(f"  OK Prompt generated ({len(prompt)} chars):\n")
        print("  " + prompt.replace("\n", "\n  "))
        return prompt
    except Exception as e:
        print(f"  FAIL Prompt gen failed: {e}")
        return None

if __name__ == "__main__":
    print("=" * 55)
    print("  Sora-2 Integration Test")
    print("=" * 55)

    gpt5_ok = test_gpt5_auth()
    vid_id  = test_sora_submit()

    prompt = asyncio.run(test_prompt_gen())

    print("\n-- Summary ------------------------------------------")
    print(f"  GPT-5 auth:       {'OK' if gpt5_ok else 'FAILED'}")
    print(f"  Sora submission:  {'OK ' + str(vid_id) if vid_id else 'FAILED'}")
    print("=" * 55)
