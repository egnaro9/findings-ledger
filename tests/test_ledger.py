"""Tests for the generator, which until now had none.

This page's whole argument is that a claim must be checkable, and it was built by a
script nothing checked. On 2026-10-07 it published 146 findings across 22
repositories directly above the sentence "every finding independently reproduced
before counting". 146 was the sweep's ESTIMATE. The replacement, 74, was reproduced
but summed MUTATIONS and FINDINGS together across repositories that counted
different units. Neither failure needed a code change to happen and neither would
have turned anything red, because there was nothing to turn red.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((HERE / "findings.json").read_text())
OWN = DATA["own_code"]


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    out = tmp_path_factory.mktemp("page")
    subprocess.run([sys.executable, "generate.py", "--no-net", "--out", str(out)],
                   cwd=HERE, check=True, capture_output=True)
    return (out / "index.html").read_text()


# ---------------------------------------------------------------------------
# the two failures that actually shipped
# ---------------------------------------------------------------------------

def test_every_row_names_its_own_unit():
    # The 74 failure: rows carried a bare integer, so a mutation count and a
    # finding count were indistinguishable and could be added together.
    for r in OWN["fixed_today"]:
        assert r["unit"].strip(), f"{r['repo']} has a number with no unit"
        assert isinstance(r["n"], int) and r["n"] > 0
        assert r["what"].strip(), f"{r['repo']} has no description"


def test_no_summed_finding_total_is_published(page):
    # The 146 failure. A total over rows whose units differ is not a quantity, so
    # the page must not render one. Guard the arithmetic, not the wording: any
    # headline equal to the sum of the rows is the bug coming back.
    row_sum = sum(r["n"] for r in OWN["fixed_today"])
    assert OWN["headline"] != row_sum, (
        f"the headline ({OWN['headline']}) equals the sum of the rows ({row_sum}), "
        "which mixes mutation counts with finding counts"
    )
    assert "findings" not in OWN["headline_unit"].lower()


def test_every_row_renders_its_unit_where_a_reader_sees_it(page):
    # Having the unit in findings.json is not the same as publishing it. Dropping
    # the unit from the template left every data assertion green while the page
    # went back to showing bare integers, which is the whole defect.
    for r in OWN["fixed_today"]:
        assert r["unit"] in page, f"{r['repo']}'s unit never reaches the page"
        i = page.index(f'<b>{r["repo"]}</b>')
        assert r["unit"] in page[i:i + 400], f"{r['repo']}'s unit is not beside its number"


def test_the_headline_is_rendered_with_its_unit(page):
    assert f'<span class="big">{OWN["headline"]}</span>' in page
    assert OWN["headline_unit"] in page


def test_the_correction_is_still_visible_on_the_page(page):
    # The retracted figure stays, because silently swapping one number for another
    # is the same failure in the other direction. If someone tidies it away this
    # goes red.
    assert "146" in page and "22 repositories" in page


# ---------------------------------------------------------------------------
# the fail-closed behaviour the page advertises
# ---------------------------------------------------------------------------

def test_offline_every_forge_status_reads_unknown(page):
    # The page promises "a status that could not be fetched reads UNKNOWN rather
    # than being guessed". --no-net is that path, so every badge must be UNKNOWN
    # and no badge may claim MERGED or OPEN from stale data.
    badges = re.findall(r'<span class="state s-([a-z]+)"', page)
    # `shipped` carries a live badge too, so it is part of the fail-closed promise.
    # Counting only external+gitlab let a new section add an unchecked badge.
    n_external = (len(DATA["external"]) + len(DATA.get("gitlab", []))
                  + len(DATA.get("shipped", [])))
    assert len(badges) == n_external, f"{len(badges)} badges for {n_external} contributions"
    assert set(badges) == {"unknown"}, f"offline build leaked a status: {set(badges)}"


def test_every_contribution_renders_a_link_to_its_forge(page):
    for f in DATA["external"]:
        assert f'https://github.com/{f["repo"]}/pull/{f["pr"]}' in page
    for g in DATA.get("gitlab", []):
        assert f'https://gitlab.com/{g["repo"]}/-/merge_requests/{g["mr"]}' in page


def test_external_links_share_the_one_named_tab(page):
    # Estate rule: externals never spawn a tab each.
    assert page.count('target="erikhill-out"') >= len(DATA["external"])
    assert 'target="_blank"' not in page


# ---------------------------------------------------------------------------
# the content is escaped, because every field here is prose with backticks in it
# ---------------------------------------------------------------------------

def test_angle_brackets_in_content_are_escaped(page, tmp_path):
    src = json.loads((HERE / "findings.json").read_text())
    src["own_code"]["fixed_today"][0]["what"] = '<script>alert(1)</script>'
    scratch = tmp_path / "findings.json"
    (tmp_path / "style.css").write_text((HERE / "style.css").read_text())
    (tmp_path / "generate.py").write_text((HERE / "generate.py").read_text())
    scratch.write_text(json.dumps(src))
    out = tmp_path / "out"
    subprocess.run([sys.executable, "generate.py", "--no-net", "--out", str(out)],
                   cwd=tmp_path, check=True, capture_output=True)
    rendered = (out / "index.html").read_text()
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;" in rendered
