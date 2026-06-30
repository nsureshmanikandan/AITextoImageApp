"""Quick test: generate 3 ad variation images and check character consistency.

Runs the real generate_ad_variations() with a TREMFYA/IBD brief, saves the
3 Flux images, prints the locked character description from each prompt, and
writes a side-by-side contact sheet for visual inspection.

Run from backend/:  python test_ad_variations.py
"""
import asyncio
import sys
import warnings
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")

from app.services.flux_service import generate_ad_variations

BRIEF = dict(
    brand_name="TREMFYA",
    product="TREMFYA (guselkumab) for IBD",
    key_message="Persistent stomach pain could be IBD. TREMFYA can help you find relief.",
    cta="Talk to your doctor",
    tone="emotional",
    script=(
        "Unexplained abdominal pain isn't normal. It could be IBD. "
        "TREMFYA offers a new path forward — talk to your doctor about relief."
    ),
    brand_description="A biologic treatment for Inflammatory Bowel Disease (IBD) / Crohn's disease.",
    target_audience="Adults with persistent, undiagnosed abdominal pain",
)


async def main():
    print("=" * 64)
    print("  Ad Variation Character-Consistency Test (TREMFYA / IBD)")
    print("=" * 64)

    variations = await generate_ad_variations(job_id=9001, media_dir="media", **BRIEF)

    print(f"\nGenerated {len(variations)} variations:\n")
    image_paths = []
    for i, v in enumerate(variations):
        print(f"-- Variation {i + 1}: {v.get('angle_name','?')} " + "-" * 30)
        print(f"  headline : {v.get('headline','')}")
        print(f"  subline  : {v.get('subline','')}")
        print(f"  cta      : {v.get('cta_text','')}")
        # First ~30 words of the prompt = the locked character description
        prompt = v.get("image_prompt", "") or ""
        print(f"  CHARACTER (prompt opening): {' '.join(prompt.split()[:35])}...")
        print(f"  image_path: {v.get('image_path','') or '(FAILED)'}")
        if v.get("image_path"):
            image_paths.append(v["image_path"])
        print()

    # Build a side-by-side contact sheet if we got images + ffmpeg is available
    if len(image_paths) >= 2:
        import subprocess
        from pathlib import Path
        out = str(Path("media") / "ad_variations_contact_sheet.png")
        inputs = []
        for p in image_paths:
            inputs += ["-i", p]
        # hstack scaled to equal height
        n = len(image_paths)
        scale_chain = "".join(f"[{i}:v]scale=-1:512[s{i}];" for i in range(n))
        stack_inputs = "".join(f"[s{i}]" for i in range(n))
        filter_complex = f"{scale_chain}{stack_inputs}hstack=inputs={n}[out]"
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[out]", out]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0:
            print(f"Contact sheet (3 images side-by-side): {out}")
        else:
            print("Contact sheet failed:", r.stderr.decode()[:200])

    print("=" * 64)
    print("Inspect the images: do they show the SAME person (hair/outfit/build)?")
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
