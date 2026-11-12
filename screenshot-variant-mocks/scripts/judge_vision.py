#!/usr/bin/env python3
"""Score screenshots with two OpenAI-compatible vision judges.

Usage: judge_vision.py rubric.json [--only a b] [--out scores.json] [--dry-run]
Environment:
  VISION_BASE_URL: API root including its version, e.g. https://api.openai.com/v1
  VISION_API_KEY_ENV: name of the variable holding the key (default OPENAI_API_KEY)
  VISION_MODELS: JSON array of exactly two distinct vision-capable model IDs

Rubric paths are relative to the rubric file. Output:
{item: {model: {criterion: score, verdict: text, biggest_risk: text} | {error: text}}}
One Chat Completions request per item per model, without retries. Dry-run validates
inputs and encodes images without credentials, network calls or fabricated scores.
"""
import argparse
import base64
import io
import json
import math
import os
from pathlib import Path
import urllib.error
import urllib.request

from PIL import Image


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward an Authorization header to a redirected endpoint."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def b64(path, maxw=1600):
    with Image.open(path) as source:
        im = source.convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, max(1, round(im.height * maxw / im.width))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def ask(base_url, api_key, model, prompt, img):
    body = {"model": model, "max_tokens": 700, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}},
        {"type": "text", "text": prompt}]}]}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
    with urllib.request.build_opener(NoRedirect).open(req, timeout=240) as response:
        result = json.load(response)
    return result["choices"][0]["message"]["content"]


def parse(text, criteria):
    result = json.loads(text)
    if not isinstance(result, dict) or set(result) != set(criteria) | {"verdict", "biggest_risk"}:
        raise ValueError("Unexpected score fields")
    for criterion in criteria:
        value = result[criterion]
        if type(value) not in (int, float) or not math.isfinite(value) or not 1 <= value <= 10:
            raise ValueError("Scores must be numbers from 1 to 10")
    if not all(isinstance(result[k], str) for k in ("verdict", "biggest_risk")):
        raise ValueError("Verdicts must be strings")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rubric", type=Path)
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        models = json.loads(os.environ.get("VISION_MODELS", "[]"))
    except ValueError:
        ap.error("VISION_MODELS must be a JSON array")
    if (not isinstance(models, list) or len(models) != 2 or
        not all(isinstance(m, str) and m.strip() for m in models) or models[0] == models[1]):
        ap.error("VISION_MODELS must contain exactly two distinct model IDs")
    base_url = os.environ.get("VISION_BASE_URL", "").strip()
    api_key = os.environ.get(os.environ.get("VISION_API_KEY_ENV", "OPENAI_API_KEY"), "")
    if not a.dry_run and (not base_url or not api_key):
        ap.error("Set VISION_BASE_URL and the API key variable named by VISION_API_KEY_ENV")
    base = a.rubric.resolve().parent
    rubric = json.loads(a.rubric.read_text())
    criteria = rubric["criteria"]
    if (not isinstance(criteria, dict) or not criteria or
        any(k in criteria for k in ("verdict", "biggest_risk", "error")) or
        not all(isinstance(v, str) for v in criteria.values())):
        ap.error("criteria must map score names to descriptions, without reserved output fields")
    if a.only and set(a.only) - rubric["items"].keys():
        ap.error("--only contains an unknown item")
    out = a.out or base / "scores.json"
    res = json.loads(out.read_text()) if a.only and out.exists() else {}
    crit = "\n".join(f"- {k}: {v}" for k, v in criteria.items())
    shape = {**dict.fromkeys(criteria, 1), "verdict": "<=30 words", "biggest_risk": "<=20 words"}
    failed = False
    for item, spec in rubric["items"].items():
        if a.only and item not in a.only:
            continue
        prompt = (rubric["context"].replace("{desc}", spec.get("desc", item)) +
            f"\n\nScore 1-10 on each criterion (10 = best). Be strict and use the whole scale.\n{crit}\n"
            f"Return ONLY JSON with this shape (replace example scores): {json.dumps(shape)}")
        img = b64(base / spec["image"])
        if a.dry_run:
            print(f"Validated {item}: image encoded, two judge requests prepared (not sent)")
            continue
        for model in models:
            try:
                score = parse(ask(base_url, api_key, model, prompt, img), criteria)
                # Providers may echo credentials in their output; redact before storing or printing.
                score = {k: v.replace(api_key, "[REDACTED]") if isinstance(v, str) else v for k, v in score.items()}
            except Exception as ex:
                # Never echo response bodies, URLs or exception messages: they can contain keys.
                detail = f"HTTP {ex.code}" if isinstance(ex, urllib.error.HTTPError) else type(ex).__name__
                score = {"error": detail}
                failed = True
            res.setdefault(item, {})[model] = score
            print(f"{item}: judge result recorded ({'error' if 'error' in score else 'ok'})", flush=True)
    if not a.dry_run:
        out.write_text(json.dumps(res, indent=2) + "\n")
        print("Saved scores")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
