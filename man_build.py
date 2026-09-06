#!/usr/bin/env python3
"""
Local-parallel documentation workflow: draft man pages with local models.

The thesis from the local-builders benchmark, applied to real work: local models
RENDER facts into roff, they do not INVENT facts. So the ground truth (every
command, flag, env var, file, gotcha) is extracted from source here, by hand,
and each section is handed to a local model as a fact sheet plus the house style
(hv.1). The model turns facts into roff; the architect verifies every line
against source and lints with groff before anything ships.

Parallelism is bench_report's shape: ONE drafter loaded, its sections drafted
concurrently (ollama serves parallel requests against one resident model without
VRAM thrash). Run it per drafter to compare who renders cleanest roff.

    python3 man_build.py                      # all drafters, both pages
    python3 man_build.py --drafters gemma4:12b
    python3 man_build.py --page bao-kit

Output: results/man/<page>.<drafter>.N  (candidate) + results/man/man_runs.jsonl.
The SHIPPED pages are assembled by the architect from the cleanest sections,
not emitted whole by this script.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

import bench

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "man")

DRAFTERS = ["gemma4:12b", "gpt-oss:20b", "qwen-3-8-27:latest"]

# The house style, taught once. Kept short: the exemplar carries most of it.
STYLE = r"""HOUSE STYLE for this man page (groff man macros, mandoc-clean):
- Use ONLY these macros: .SH (section), .SS (subsection), .TP (tagged paragraph),
  .BI/.BR/.RI/.RB (alternating bold/italic/roman), .B .I (whole-line font),
  .PP (paragraph break), .nf/.fi (no-fill literal block for command examples).
- Escape every literal hyphen in a flag or option as \- (backslash hyphen).
- A .TP entry is: the .TP macro, then ONE tag line (the command/term, bolded),
  then the description lines. Example of one entry:
    .TP
    .BI unseal
    Morning ritual: the PC sleeps at night and the vault seals, so unseal it
    with the stored key.
- No prose outside a section. No markdown. No code fences. No .TH line (the
  assembler adds it). Start your output at the .SH line for THIS section only.
Here is a real entry from a sibling page (hv.1), for tone and macro use:
    .TP
    .BI inspect " ID"
    Print one ticket: title, status, resolution, full comment thread.
    .I ID
    is the 10-character prefix shown by
    .BR proposals .
"""

def sec_prompt(heading, facts):
    return (STYLE + f"\n\nWrite ONLY the roff for the .SH {heading} section of a man "
            f"page, using ONLY these facts. Do not add any command, flag, path, or "
            f"behaviour that is not stated here. If a fact names an exact string, "
            f"reproduce it exactly.\n\nFACTS:\n{facts}\n\nOutput only roff, starting "
            f"with `.SH {heading}`.")


# --- ground truth: bao-kit.1 -----------------------------------------------
# every fact below is read from /data/NuCode/Bao/bin/bao-kit (the source).

BAO_KIT = {
  "DESCRIPTION": ("DESCRIPTION",
    "bao-kit is a single bash script wrapping the whole personal-Vault workflow for "
    "an OpenBao instance on the LAN. One operator (ziggy), per-project secrets, "
    "per-session tokens, tightly scoped subagent tokens. Personal-grade by design. "
    "It always exports BAO_ADDR and BAO_CACERT and sets BAO_FORMAT=json before "
    "running bao. If BAO_TOKEN is unset and ~/.config/openbao/token is readable, it "
    "loads that cached token and silently renews it. Secrets never print unless you "
    "explicitly ask (the unwrap command, or running bao kv get yourself). "
    "Usage: bao-kit COMMAND [args]. It requires bao and python3 on PATH."),
  "COMMANDS_SETUP": ("COMMANDS",
    "Render each as a .TP entry under a .SS Setup and authentication subsection. "
    "Commands, exact behaviour:\n"
    "- env : print shell exports (BAO_ADDR, BAO_CACERT, and BAO_TOKEN if a login is "
    "cached); use as: eval \"$(bao-kit env)\".\n"
    "- init : one-time setup. Initialises the vault with a single unseal key share, "
    "unseals it, enables the kv v2 secrets engine at kv/, enables userpass auth, "
    "enables the file audit device, writes the operator policy. Writes the unseal "
    "key and root token to ~/.config/openbao/init.json at mode 600.\n"
    "- unseal : the morning ritual. The PC sleeps at night and the vault seals; this "
    "reads the stored unseal key from init.json and unseals, then prints status.\n"
    "- user : create or reset the ziggy operator user. Prompts for a password, so "
    "run it in a terminal. The user gets the operator policy and 12h tokens (24h max).\n"
    "- login : log in as ziggy. Prompts for the password, obtains a 12h operator "
    "token, and caches it in ~/.config/openbao/token."),
  "COMMANDS_SECRETS": ("COMMANDS",
    "Render each as a .TP entry under a .SS Projects and secrets subsection. "
    "Commands, exact behaviour:\n"
    "- project NAME : create or refresh the policy project-NAME, granting read on "
    "kv/NAME/* , and a token role project-NAME (orphan service tokens, 24h max) "
    "that mints session tokens carrying that policy.\n"
    "- put NAME/KEY field=value ... : store a secret at kv/NAME/KEY. It MERGES the "
    "given fields into an existing secret (it patches; it does not replace the whole "
    "secret), and creates the secret if absent.\n"
    "- status : print seal state and health (sealed, initialized, version) and, if a "
    "token is loaded, who am I (display name, policies, ttl, metadata)."),
  "COMMANDS_DELEGATION": ("COMMANDS",
    "Render each as a .TP entry under a .SS Sessions and delegation subsection. "
    "Commands, exact behaviour:\n"
    "- session NAME [-- CMD...] : mint an 8h token scoped to project NAME (policy "
    "project-NAME), run CMD with BAO_TOKEN, BAO_SESSION and BAO_PROJECT set in its "
    "environment, and revoke the token when CMD exits. CMD defaults to claude. "
    "Revocation cascades to any child tokens the session minted.\n"
    "- sub [TTL] [USES] : run from inside a session. Mint a use-limited child token "
    "for a subagent. TTL defaults to 30m, USES defaults to 2.\n"
    "- wrap NAME/KEY [TTL] : print a single-use response-wrapping token that carries "
    "the secret at kv/NAME/KEY. TTL defaults to 5m. Hand the token to a subagent.\n"
    "- unwrap TOKEN : the subagent side of wrap. Unwrap the token and print the "
    "secret fields as KEY=VALUE lines. This is one of the two commands that print a "
    "secret.\n"
    "- with NAME/KEY:field=ENV[,field=ENV] -- CMD... : read the secret at "
    "kv/NAME/KEY and run CMD with each named field placed in the child's environment "
    "as the given ENV variable. The secret is only ever in the child's environment, "
    "never printed."),
  "ENVIRONMENT": ("ENVIRONMENT",
    "Render as .TP entries. Variables:\n"
    "- BAO_ADDR : the vault address. Defaults to https://192.168.88.18:8200 .\n"
    "- BAO_CACERT : path to the self-signed CA cert. Defaults to the tls/bao.crt "
    "file under the bao-kit install directory.\n"
    "- BAO_FORMAT : bao-kit sets this to json internally so it can parse output. "
    "Note that with json format, bao's -field= prints a quoted string.\n"
    "- BAO_TOKEN : the auth token. If set in the environment it takes precedence over "
    "the cached token file (this is deliberate for scoped sessions, but a STALE "
    "exported BAO_TOKEN will shadow a fresh login; see NOTES).\n"
    "- BAO_SESSION, BAO_PROJECT : set by the session command in the child "
    "environment, naming the session id and project."),
  "FILES": ("FILES",
    "Render as .TP entries. Files:\n"
    "- ~/.config/openbao/init.json : the unseal key and root token from init, mode "
    "600. Required by unseal.\n"
    "- ~/.config/openbao/token : the cached operator login token, mode 600, loaded "
    "when BAO_TOKEN is unset.\n"
    "- tls/bao.crt : the self-signed CA certificate, under the install directory.\n"
    "- policies/operator.hcl : the operator policy, written by init."),
  "NOTES": ("NOTES",
    "Render as .TP or .PP entries. Each is a real gotcha:\n"
    "- A stale BAO_TOKEN in the shell shadows a fresh login. bao-kit only loads the "
    "cached token file when BAO_TOKEN is unset, so an exported token left over from a "
    "previous session keeps being used and every call fails with a 403 even right "
    "after login. Fix: unset BAO_TOKEN before the command.\n"
    "- put merges fields into an existing secret rather than replacing it, so adding "
    "one field does not erase the others. (A plain bao kv put would replace the whole "
    "secret.)\n"
    "- A non-root token can only mint child tokens whose policies are a subset of its "
    "own; sessions mint through the token role project-NAME created by the project "
    "command.\n"
    "- The vault seals whenever the host reboots; unseal is a daily step."),
  "SEE_ALSO": ("SEE ALSO",
    "Render as a short .SH SEE ALSO. Facts: the raw OpenBao CLI is bao(1). The local "
    "deployment is documented in bao(1) as configured here (same box). The vault "
    "repo README at /data/NuCode/Bao/README.md is authoritative. End with a line: "
    "read this page without installing it: man ./docs/bao-kit.1"),
}

# --- ground truth: bao.1 (OpenBao as deployed on the NuCode LAN) ------------

BAO_LOCAL = {
  "DESCRIPTION": ("DESCRIPTION",
    "bao is the OpenBao command-line client (a static Go binary, version 2.6.2 on "
    "this box). This page documents OpenBao AS DEPLOYED on the NuCode LAN, not the "
    "full upstream CLI (for that run: bao -h , or see the OpenBao docs). The vault "
    "runs as a Docker container named bao from /data/NuCode/Bao, reachable at "
    "https://192.168.88.18:8200 on the LAN and loopback only, behind a self-signed "
    "certificate. Day to day you drive it through bao-kit(1), which sets the address, "
    "the CA cert and the token for you; reach for raw bao only for things bao-kit "
    "does not wrap."),
  "DEPLOYMENT": ("DEPLOYMENT",
    "Render as .TP or .PP. Facts:\n"
    "- The vault is a docker compose service named bao, defined in "
    "/data/NuCode/Bao/docker-compose.yml , image openbao/openbao:2.6.2 .\n"
    "- Raft storage lives on a named docker volume, so recreating the container does "
    "not lose data.\n"
    "- The listener binds 0.0.0.0:8200 inside the container; the host publishes it on "
    "127.0.0.1:8200 and 192.168.88.18:8200 .\n"
    "- TLS is a self-signed cert; clients must trust tls/bao.crt (BAO_CACERT).\n"
    "- The audit device and the kv v2 engine at kv/ are enabled at init time."),
  "ENVIRONMENT": ("ENVIRONMENT",
    "Render as .TP entries. Every raw bao call needs these; bao-kit sets them.\n"
    "- BAO_ADDR : https://192.168.88.18:8200 .\n"
    "- BAO_CACERT : path to tls/bao.crt , so the client trusts the self-signed cert.\n"
    "- BAO_TOKEN : the auth token; if unset, bao-kit loads the cached login from "
    "~/.config/openbao/token .\n"
    "The quickest way to set all three is: eval \"$(bao-kit env)\" ."),
  "RITUAL": ("DAILY USE",
    "Render as .PP/.nf. Facts: the host sleeps at night and the vault SEALS on every "
    "boot, so the day starts sealed. The morning ritual is:\n"
    "  bao-kit unseal    (reads the stored key, unseals)\n"
    "  bao-kit login     (caches a 12h operator token)\n"
    "After that, bao-kit status should show sealed: False and a valid token. Raw "
    "equivalents exist (bao operator unseal, bao login) but the kit is the path."),
  "COMMANDS": ("COMMANDS YOU USE",
    "Render as .TP entries. This is the SUBSET of the bao CLI used on this box; the "
    "full command set is in bao -h .\n"
    "- bao status : seal and HA status.\n"
    "- bao operator unseal KEY : submit an unseal key share (bao-kit unseal wraps "
    "this).\n"
    "- bao kv get -mount=kv PATH : read a secret (prints it; mind the transcript).\n"
    "- bao kv put -mount=kv PATH field=value : replace a secret (whole secret).\n"
    "- bao kv patch -mount=kv PATH field=value : merge fields into a secret (this is "
    "what bao-kit put uses).\n"
    "- bao token lookup / bao token create : inspect or mint tokens.\n"
    "- bao login -method=userpass username=ziggy : authenticate.\n"
    "- bao unwrap TOKEN : unwrap a response-wrapping token."),
  "TROUBLESHOOTING": ("TROUBLESHOOTING",
    "Render as .TP entries, symptom then fix. Real failure modes seen on this box:\n"
    "- Connection refused on 8200 though docker ps shows the container Up: Docker "
    "started the container without installing the host port publish (docker inspect "
    "shows PortBindings set but NetworkSettings.Ports empty; nothing listens on host "
    ":8200). It follows iptables churn from the LAN NAT link. Fix: recreate, do not "
    "just restart: cd /data/NuCode/Bao && docker compose down && docker compose up "
    "-d . The raft data is on the named volume, so nothing is lost. Verify with "
    "docker port bao (expect both 127.0.0.1:8200 and 192.168.88.18:8200).\n"
    "- Every call 403s right after login: a stale exported BAO_TOKEN is shadowing the "
    "fresh cached token. Fix: unset BAO_TOKEN before the command.\n"
    "- sealed: True after a reboot: expected; run bao-kit unseal ."),
  "FILES": ("FILES",
    "Render as .TP entries.\n"
    "- /data/NuCode/Bao/docker-compose.yml : the compose service.\n"
    "- /data/NuCode/Bao/tls/bao.crt : the self-signed CA cert (BAO_CACERT).\n"
    "- /data/NuCode/Bao/config/ : the OpenBao server config (declares the listener "
    "and the file audit device).\n"
    "- ~/.config/openbao/init.json : unseal key and root token, mode 600.\n"
    "- ~/.config/openbao/token : cached operator login, mode 600."),
  "SEE_ALSO": ("SEE ALSO",
    "Render as a short .SH SEE ALSO. Facts: bao-kit(1) is the wrapper you use day to "
    "day. The vault repo README at /data/NuCode/Bao/README.md is authoritative. The "
    "full upstream CLI is in bao -h and the OpenBao documentation. End with a line: "
    "read this page without installing it: man ./docs/bao.1"),
}

PAGES = {"bao-kit": BAO_KIT, "bao": BAO_LOCAL}


def groff_lint(text):
    """Return list of groff warnings for a full man page (empty = clean)."""
    with tempfile.NamedTemporaryFile("w", suffix=".1", delete=False) as f:
        f.write(text); path = f.name
    try:
        r = subprocess.run(["groff", "-man", "-ww", "-z", path],
                           capture_output=True, text=True, timeout=30)
        warns = [l for l in (r.stderr or "").splitlines() if l.strip()]
        return warns
    finally:
        os.unlink(path)


def th_line(page):
    name = page.upper().replace("-", "\\-")
    return '.TH ' + name + ' 1 "2026-09-06" "NuCode" "LAN vault"'


def draft_page(drafter, page, spec):
    bench.stop_all()
    bench.chat(drafter, "Reply with the single word: ready", num_predict=16)

    def one(item):
        key, (heading, facts) = item
        r = bench.chat(drafter, sec_prompt(heading, facts))
        body = re.sub(r"^```[a-zA-Z0-9]*\n?|```$", "", r["content"].strip(), flags=re.M)
        return key, body.strip(), r["eval_tok"], r["eval_ms"]

    with ThreadPoolExecutor(max_workers=len(spec)) as ex:
        got = list(ex.map(one, spec.items()))
    # assemble in spec order
    order = list(spec.keys())
    got.sort(key=lambda t: order.index(t[0]))
    doc = th_line(page) + "\n" + f".SH NAME\n{page} \\- " + \
        ("the personal-Vault workflow wrapper" if page == "bao-kit"
         else "OpenBao vault as deployed on the NuCode LAN") + "\n"
    doc += "\n".join(b for _, b, _, _ in got) + "\n"
    return doc, got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafters", default=",".join(DRAFTERS))
    ap.add_argument("--page", default="", help="bao-kit | bao (default: both)")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    drafters = [d.strip() for d in args.drafters.split(",") if d.strip()]
    pages = [args.page] if args.page else list(PAGES)

    for page in pages:
        spec = PAGES[page]
        print(f"\n#### {page}.1  ({len(spec)} sections) ####", flush=True)
        for d in drafters:
            place = None
            doc, got = draft_page(d, page, spec)
            place = bench.placement(d)
            warns = groff_lint(doc)
            n = len([g for g in got])
            cand = os.path.join(OUT, f"{page}.{d.replace(':','_').replace('/','_')}.1")
            with open(cand, "w") as f:
                f.write(doc)
            # per-section groff cleanliness: lint each section wrapped in a minimal TH
            sec_clean = 0
            for key, body, _, _ in got:
                w = groff_lint(th_line(page) + "\n" + body + "\n")
                if not w:
                    sec_clean += 1
            tok = sum(g[2] for g in got)
            secs = round(max(g[3] for g in got) / 1000, 1)
            rec = dict(page=page, drafter=d, placement=place, sections=n,
                       sec_clean=sec_clean, page_warns=len(warns), tok=tok,
                       par_sec=secs, candidate=os.path.basename(cand))
            with open(os.path.join(OUT, "man_runs.jsonl"), "a") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"  {d:22} {place:8} sec-clean {sec_clean}/{n}  page-warns "
                  f"{len(warns):2}  {tok:>5} tok  {secs:5.1f}s (parallel) -> {os.path.basename(cand)}",
                  flush=True)
            if warns:
                for w in warns[:4]:
                    print(f"       ! {w}", flush=True)


if __name__ == "__main__":
    main()
