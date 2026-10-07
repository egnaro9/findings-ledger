# findings-ledger

Source for **erikhill.dev/findings**: defects found by planting the defect each check claims
to catch, in other people's code and in my own.

`findings.json` is the data, `generate.py` renders it, and the output is deployed into
`egnaro9.github.io/findings/`. The generated `index.html` is not tracked here, because the
deployed copy is the one under version control.

    python generate.py --out ../egnaro9.github.io/findings   # deploy target
    python generate.py --no-net                              # offline, every status UNKNOWN
    python -m pytest tests/                                  # 9 tests

Every forge status on the page is fetched at build time, so a merged PR cannot sit there as
open. A status that cannot be fetched reads UNKNOWN and is never guessed or carried over.

## Why this repository has tests

The page argues that a claim has to be checkable, and for its first day it was built by a
script nothing checked. It published **146 findings across 22 repositories** directly above
the sentence "every finding independently reproduced before counting". 146 was the sweep's
*estimate*; measured, the per-repository numbers moved up to 3x in both directions. The
obvious correction was the reproduced total, 74, which had the same flaw one level down: it
summed mutation counts and finding counts across repositories that recorded different units.

So no summed finding total is published. The headline is the one figure that is uniformly
reproducible from the diffs, every row names its own unit, and `tests/test_ledger.py` fails
if a headline ever equals the sum of the rows again, if a unit stops reaching the page, or if
the retracted figure is tidied out of the correction note.

Each test was proven by planting the defect it claims to catch. One was found that way: the
unit could be dropped from the template with every data assertion still green, so the page
reverted to bare integers while the tests said otherwise.
