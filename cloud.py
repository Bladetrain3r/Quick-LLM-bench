#!/usr/bin/env python3
"""
Cloud (Anthropic) call helper for the E2E benchmark's control arm and orchestrator
stages. Reads the API key ONLY from the environment — never a literal, never
printed — so it is always invoked through the vault:

    bao-kit with village/cloudkeys:<field>=ANTHROPIC_API_KEY -- python3 cloud.py "prompt"

Returns the same shape as bench.chat (content + token counts + wall time) so the
pipeline can treat a cloud call and a local call uniformly. Uses urllib to avoid
a hard dependency on the anthropic SDK.
"""
import json
import os
import sys
import time
import urllib.request

API = "https://api.anthropic.com/v1/messages"
HAIKU = "claude-haiku-4-5-20251001"


def call(prompt, model=HAIKU, system=None, max_tokens=2000, thinking=False):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("no ANTHROPIC_API_KEY — run under: "
                         "bao-kit with village/cloudkeys:<field>=ANTHROPIC_API_KEY -- ...")
    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    if thinking:
        body["thinking"] = {"type": "enabled", "budget_tokens": max_tokens // 2}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    t = time.time()
    o = json.load(urllib.request.urlopen(req, timeout=180))
    dt = round(time.time() - t, 1)
    text = "".join(b.get("text", "") for b in o.get("content", []) if b.get("type") == "text")
    u = o.get("usage", {})
    return dict(content=text, model=o.get("model"), sec=dt,
                in_tok=u.get("input_tokens", 0), out_tok=u.get("output_tokens", 0))


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly the word PONG and nothing else."
    r = call(prompt)
    print(f"model={r['model']}  in={r['in_tok']} tok  out={r['out_tok']} tok  {r['sec']}s")
    print("--- content ---")
    print(r["content"][:800])
