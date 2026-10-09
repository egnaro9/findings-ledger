#!/usr/bin/env python3
"""Render the findings ledger from findings.json, with LIVE status pulled from the forges.

The point of generating rather than hand-writing: a hand-maintained claim rots. A measured
audit of this author's own repository descriptions found 19 problems in 56 claims. Every
status on this page is fetched at build time from the GitHub or GitLab API, so a merged PR
cannot sit here as "open" and a closed one cannot sit here as "merged".

A status that cannot be fetched reads UNKNOWN. It is never guessed and never carried over
from a previous build, because a page about checks that cannot fail has no business
asserting something it did not check.

  python generate.py                 # writes index.html next to this file
  python generate.py --no-net        # every status UNKNOWN, for offline editing
  python generate.py --out DIR       # write index.html and style.css into DIR
"""
from __future__ import annotations

import html
import json
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
UNKNOWN = ("UNKNOWN", "status could not be fetched")
OUT_TAB = 'target="erikhill-out"'   # estate rule: every external link shares one named tab


def gh_pr(repo: str, number: int) -> tuple[str, str]:
    """(state, detail) for a GitHub PR, via `gh` so auth and rate limits are handled."""
    try:
        p = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{number}",
             "--jq", '[.state, (.merged|tostring), .created_at]|join("|")'],
            capture_output=True, text=True, timeout=20)
        if p.returncode != 0:
            return UNKNOWN
        state, merged, created = p.stdout.strip().split("|")
        if merged == "true":
            return "MERGED", f"merged, opened {created[:10]}"
        return state.upper(), f"{state}, opened {created[:10]}"
    except Exception:
        return UNKNOWN


def gl_mr(project: str, iid: int) -> tuple[str, str]:
    try:
        url = (f"https://gitlab.com/api/v4/projects/"
               f"{urllib.parse.quote(project, safe='')}/merge_requests/{iid}")
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.load(r)
        return d["state"].upper(), f"{d['state']}, opened {d['created_at'][:10]}"
    except Exception:
        return UNKNOWN


def e(s) -> str:
    return html.escape(str(s))


def render(data: dict, live: bool) -> str:
    m, own = data["method"], data["own_code"]
    out = []
    add = out.append

    add('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">')
    add('<link rel="icon" type="image/svg+xml" href="/favicon.svg">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add('<meta name="description" content="Defects found in other people\'s code and in my own, '
        'by planting the defect each check claims to catch.">')
    add("<title>Checks That Cannot Fail</title>")
    add("<style>" + (HERE / "style.css").read_text() + "</style>")
    add("</head>\n<body>\n<div class=\"wrap\">\n<div class=\"col\">")

    add("<header>")
    add('<nav class="contact" style="margin:0 0 30px" aria-label="Site">'
        '<span class="chip"><a href="../">&larr; Home</a></span>'
        '<span class="chip"><a href="../about/">About</a></span>'
        '<span class="chip"><a href="../resume/">R&eacute;sum&eacute;</a></span></nav>')
    add('<div class="label"><span class="tick">//</span> Findings</div>')
    add("<h1>Checks that cannot fail</h1>")
    add(f'<p class="thesis">{e(m["one_line"])}</p>')
    add("</header>")

    add('<h2 class="sec">Method</h2>')
    add('<div class="card method"><ol>')
    for step in m["procedure"]:
        add(f"<li>{e(step)}</li>")
    add(f'</ol><p class="why">{e(m["why"])}</p></div>')

    add('<h2 class="sec">Found in other people\'s code</h2>')
    for f in data["external"]:
        state, detail = gh_pr(f["repo"], f["pr"]) if live else UNKNOWN
        url = f'https://github.com/{f["repo"]}/pull/{f["pr"]}'
        add('<article class="finding"><header>'
            f'<a class="repo" href="{e(url)}" {OUT_TAB}>{e(f["repo"])}#{f["pr"]}</a>'
            f'<span class="state s-{e(state.lower())}" title="{e(detail)}">{e(state)}</span>'
            "</header><dl>"
            f'<dt>The check claimed</dt><dd>{e(f["claimed"])}</dd>'
            f'<dt>What it actually did</dt><dd>{e(f["actual"])}</dd>'
            f'<dt>How it was proven</dt><dd>{e(f["proven"])}</dd>'
            f'<dt>Delivered</dt><dd>{e(f["delivered"])}</dd>'
            "</dl></article>")
    for g in data["gitlab"]:
        state, detail = gl_mr(g["repo"], g["mr"]) if live else UNKNOWN
        url = f'https://gitlab.com/{g["repo"]}/-/merge_requests/{g["mr"]}'
        add('<article class="finding"><header>'
            f'<a class="repo" href="{e(url)}" {OUT_TAB}>{e(g["repo"])}!{g["mr"]}</a>'
            f'<span class="state s-{e(state.lower())}" title="{e(detail)}">{e(state)}</span>'
            "</header><dl>"
            f'<dt>What it actually did</dt><dd>{e(g["actual"])}</dd>'
            f'<dt>How it was proven</dt><dd>{e(g["proven"])}</dd>'
            "</dl></article>")

    if data.get("shipped"):
        # Deliberately NOT in the ledger above. That one asks what a check claimed and
        # what it actually did; a feature answers neither. Listed so the contribution
        # claims elsewhere on the estate resolve to something.
        add('<h2 class="sec">Shipped upstream, not a defect</h2>')
        add('<p class="why">Kept out of the ledger above on purpose. That one is for '
            'checks that could not fail, and these are features.</p>')
        for sh in data["shipped"]:
            state, detail = gh_pr(sh["repo"], sh["pr"]) if live else UNKNOWN
            url = f'https://github.com/{sh["repo"]}/pull/{sh["pr"]}'
            add(f'<article class="shipped"><h3>{e(sh["title"])}</h3>'
                f'<p class="where"><a href="{e(url)}" {OUT_TAB}>{e(sh["repo"])}#{sh["pr"]}</a>'
                f' &middot; <span class="state s-{e(state.lower())}" title="{e(detail)}">{e(state)}</span>'
                f' &middot; {e(sh["scale"])}</p>'
                f'<p>{e(sh["what"])}</p><p>{e(sh["why_hard"])}</p></article>')
    add('<h2 class="sec">Found in my own</h2>')
    add('<div class="card own">'
        f'<div><span class="big">{own["headline"]}</span> {e(own["headline_unit"])}</div>'
        f'<p style="color:var(--fg-dim);font:.94rem/1.55 var(--sans);margin:10px 0 0">'
        f'{e(own["note"])}</p><ul>')
    for r in own["fixed_today"]:
        add(f'<li><b>{e(r["repo"])}</b><span class="n">{r["n"]}</span>'
            f'<i class="unit">{e(r["unit"])}</i> {e(r["what"])}</li>')
    add("</ul></div>")

    add('<h2 class="sec">Where I was wrong</h2>')
    for c in data["corrected"]:
        add(f'<article class="correction"><h3>{e(c["what"])}</h3>'
            f'<p class="where">{e(c["where"])}</p><p>{e(c["outcome"])}</p></article>')

    add('<div class="foot">Every status above is fetched from the GitHub and GitLab APIs when '
        "this page is built, so a claim here cannot drift from the forge. A status that could "
        "not be fetched reads UNKNOWN rather than being guessed.<br>"
        f'<a href="https://github.com/egnaro9" {OUT_TAB}>github.com/egnaro9</a></div>')

    add("</div>\n</div>\n</body>\n</html>")
    return "\n".join(out) + "\n"


def main() -> int:
    live = "--no-net" not in sys.argv
    dest = HERE
    if "--out" in sys.argv:
        dest = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
        dest.mkdir(parents=True, exist_ok=True)
    data = json.loads((HERE / "findings.json").read_text())
    (dest / "index.html").write_text(render(data, live), encoding="utf-8")
    print(f"wrote {dest}/index.html (live={live})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
