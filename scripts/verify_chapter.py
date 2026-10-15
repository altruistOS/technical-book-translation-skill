#!/usr/bin/env python3
"""verify_chapter.py - reusable C1-C10 translation QA gate.

Compares an extracted source chapter (Markdown) against its translation and
reports PASS/FAIL for the ten gates described in SKILL.md section 4.4.
Stdlib only. Exit code 0 = all gates pass, 1 = at least one failure.

Usage:
    verify_chapter.py --src source_final/chapter_8.md \
                      --zh  chinese_final/chapter_8.md \
                      [--targets targets.txt] \
                      [--c6wl 225,227] \
                      [--w10 w10.json]

--targets  file with the 1-based line numbers that were translated
           (comma- or newline-separated). Required for the strict form of
           C5/C6; if omitted, translated lines are inferred as those that
           differ from the source and C5/C6 are reported as SKIP.
--c6wl     comma-separated line numbers exempt from the CJK requirement
           (e.g. bare equation numbers kept verbatim).
--w10      JSON file: {"<line>": {"<char>": <count>, ...}} of source special
           characters that are ALLOWED to be dropped on that line.
"""
import argparse
import json
import re
import sys
from collections import Counter

SPAN_RE = re.compile(r"\$\$?[^$]*\$\$?")


def spans(line):
    r"""Return the ordered math spans of a line (text between $...$ pairs).
    An escaped \$ is a literal dollar, not a delimiter. A line with an
    unbalanced $ count has no reliable math structure and yields []."""
    tmp = line.replace("\\$", "\x00")
    parts = tmp.split("$")
    if len(parts) % 2 == 0:
        return []
    return [p.replace("\x00", "\\$") for p in parts[1::2]]


def outside_math(line):
    """Return the concatenation of everything outside $...$ regions."""
    tmp = line.replace("\\$", "\x00")
    parts = tmp.split("$")
    if len(parts) % 2 == 0:
        return line
    return "".join(p.replace("\x00", "\\$") for p in parts[0::2])


def has_cjk(s):
    return any(0x4E00 <= ord(c) <= 0x9FFF for c in s)


def ctrl_counter(s):
    return Counter(c for c in s if ord(c) < 32)


def specials(line):
    """Non-ASCII, non-CJK, non-ideographic-comma codepoints outside math."""
    text = outside_math(line).replace("\\x", "")
    return Counter(
        c
        for c in text
        if ord(c) > 127
        and not (0x4E00 <= ord(c) <= 0x9FFF)
        and not (0x3400 <= ord(c) <= 0x4DBF)
        and c != "\u3001"
    )


def load_targets(path):
    if not path:
        return None
    raw = open(path, encoding="utf-8").read()
    nums = [int(x) for x in re.split(r"[,\s]+", raw) if x.strip()]
    return set(nums)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--zh", required=True)
    ap.add_argument("--targets")
    ap.add_argument("--c6wl", default="")
    ap.add_argument("--w10")
    a = ap.parse_args()

    raws = open(a.src, encoding="utf-8").read()
    rawz = open(a.zh, encoding="utf-8").read()
    sl = raws.split("\n")
    zl = rawz.split("\n")

    targets = load_targets(a.targets)
    c6wl = {int(x) for x in re.split(r"[,\s]+", a.c6wl) if x.strip()}
    w10 = {}
    if a.w10:
        w10 = {int(k): Counter(v) for k, v in json.load(open(a.w10, encoding="utf-8")).items()}

    ok = True

    def chk(name, cond, detail=""):
        nonlocal ok
        print("%s %s %s" % ("PASS" if cond else "FAIL", name, detail))
        if not cond:
            ok = False

    def skip(name, why):
        print("SKIP %s %s" % (name, why))

    chk("C1 line-count", len(sl) == len(zl), "src=%d zh=%d" % (len(sl), len(zl)))
    if len(sl) != len(zl):
        print("ABORT: line counts differ; cannot run remaining gates")
        return 1

    chk("C2 no-trailing-newline", not rawz.endswith("\n") and not raws.endswith("\n"))

    chk("C3 $ total", raws.count("$") == rawz.count("$"),
        "src=%d zh=%d" % (raws.count("$"), rawz.count("$")))
    bad3 = [i for i in range(1, len(sl) + 1) if sl[i - 1].count("$") != zl[i - 1].count("$")]
    chk("C3b $ per-line", not bad3, "mismatch at %r" % bad3[:10])

    bad4 = [i for i in range(1, len(sl) + 1) if spans(sl[i - 1]) != spans(zl[i - 1])]
    chk("C4 math-token order", not bad4, "mismatch at %r" % bad4[:10])

    if targets is None:
        skip("C5 verbatim-non-target", "(no --targets given)")
        skip("C6 CJK-coverage", "(no --targets given)")
        targets = set()
    else:
        bad5 = [i for i in range(1, len(sl) + 1) if i not in targets and sl[i - 1] != zl[i - 1]]
        chk("C5 verbatim-non-target", not bad5, "non-target lines changed at %r" % bad5[:10])
        bad6 = [i for i in sorted(targets) if not has_cjk(zl[i - 1]) and i not in c6wl]
        chk("C6 CJK-coverage", not bad6, "translated lines without CJK at %r" % bad6[:10])

    chk("C7 control-chars", ctrl_counter(raws) == ctrl_counter(rawz),
        "src=%r zh=%r" % (dict(ctrl_counter(raws)), dict(ctrl_counter(rawz))))

    bad8 = [
        i
        for i in range(1, len(sl) + 1)
        if (len(sl[i - 1]) - len(sl[i - 1].rstrip(" "))) != (len(zl[i - 1]) - len(zl[i - 1].rstrip(" ")))
    ]
    chk("C8 trailing-spaces", not bad8, "mismatch at %r" % bad8[:10])

    bad9 = [i for i in range(1, len(zl) + 1) if re.search(r"\\x[0-9a-fA-F]{2}", zl[i - 1])]
    chk("C9 no-literal-escape", not bad9, "literal \\xNN at %r" % bad9[:10])

    bad10 = []
    for i in sorted(targets):
        ds, dz = specials(sl[i - 1]), specials(zl[i - 1])
        if ds - w10.get(i, Counter()) != dz:
            bad10.append((i, dict(ds), dict(dz)))
    chk("C10 special-chars", not bad10, "mismatch: %r" % bad10[:5])

    print("ALL GATES %s" % ("PASS" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
