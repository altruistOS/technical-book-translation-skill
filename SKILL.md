---
name: technical-book-translation
description: Use when turning a technical book or PDF into a translated Markdown edition while preserving equations exactly - includes MinerU/OCR extraction, hand-annotated PDFs (comment boxes recognized as images), figure/image handling, chapter page-range mapping, and verifying translation fidelity.
---

# Skill: Technical Book Translation

A rigorous end-to-end pipeline for converting technical PDFs (via MinerU OCR) into high-fidelity, equation-accurate, bilingual Markdown files, with proper git hygiene and repo-ready deliverables.

---

## 0. Pre-Production Setup

### 0.1 Repository Initialization

Before any extraction or translation work begins, initialize the repository with proper hygiene:

```bash
git init
```

### 0.2 .gitignore (CRITICAL — set up BEFORE first commit)

The `.gitignore` must use a **deny-by-default** pattern to prevent intermediate artifacts from being tracked:

```gitignore
# Ignore everything by default
/*
!/.gitkeep

# Track only clean output directories
!/.gitignore
!/README.md
# --- single-book layout ---
!/chinese_final
!/source_final
!/images
!/chinese_final/**
!/source_final/**
!/images/**
# --- multi-book layout (one folder per book, each with the same three dirs) ---
!/*/README.md
!/*/source_final/
!/*/source_final/**
!/*/chinese_final/
!/*/chinese_final/**
!/*/images/
!/*/images/**

# macOS
.DS_Store

# Project working files (NOT for the repo)
*.sh
*.log
*.pdf
AGENTS.md
.codegraph/
.omo/
.opencode/
mineru_test/
mineru_raw/
```

> Pick ONE layout. The multi-book block is what most real projects need (e.g. `coding_signal_processing/`, `hdd_servo_systems/`, … each holding `source_final/ chinese_final/ images/`). The `!/*/...` globs re-include those nested dirs while `/*` still blocks everything else.

> **⚠️ CRITICAL: `.gitignore` does NOT retroactively untrack files.**
> Files that were committed BEFORE .gitignore was set up will STILL be tracked and pushed.
> To remove them: `git rm --cached <file>` then commit.

### 0.3 Required Directory Structure

```
<repo-root>/
├── .gitignore
├── README.md
├── source_final/       # Clean extracted Markdown chapters (MinerU OCR, source language)
│   ├── chapter_1.md
│   ├── chapter_2.md
│   └── ...
├── chinese_final/      # Chinese translations
│   ├── chapter_1.md
│   ├── chapter_2.md
│   └── ...
└── images/             # ALL book images (NOT under source_final/)
    ├── chapter_1/
    ├── chapter_2/
    └── appendix/
```

> **IMPORTANT**: Images should be at the repo root `images/`, NOT under `source_final/images/`.
> This keeps paths clean whether viewing from project root or subdirectory.

### 0.4 Initial Git Commit

```bash
git add .gitignore
git commit -m "Initial commit: .gitignore"
```

---

## 1. Phase 0: Structural Decomposition & Page Range Verification (CRITICAL)

**Common failure mode**: After extracting + translating a chapter, the final section(s) are missing because the calculated page range was too narrow. This happens with EVERY translation project if not actively prevented.

### 1.1 Principle: Anchor by Next Chapter's Start

The most reliable page range for chapter N is:

```
page_range = [ch_N_first_page, ch_{N+1}_first_page - 1]
```

NOT the TOC's stated range. TOC ranges are unreliable because:
- PDF pagination may have offset from printed page numbers
- Appendices or extra content may attach to the chapter end
- TOC may list a range that excludes back matter embedded within the chapter

### 1.2 Workflow: Complete Page Mapping

#### Step A — Build a Physical Page Map

For EVERY chapter (including appendices, references, index), determine the **exact physical PDF page** where it starts:

| Content | Logical Page (TOC) | Physical PDF Page | How to Find |
|---------|-------------------|-------------------|-------------|
| Ch1 | 1 | P14 | Open PDF, scroll to Ch1 title |
| Ch2 | 59 | ? | Open PDF, scroll to Ch2 title |
| Ch_N | ... | ... | ... |
| Appendix A | ... | ... | ... |
| References | ... | ... | ... |
| Index | ... | ... | ... |

**Method**: Use `pdfinfo` to get total pages, then open the PDF at the approximate location. Scroll until you see the chapter title. Note the PDF reader's page number. This is the one true source of truth.

#### Step B — Calculate Extraction Ranges

For each chapter N (except the last):

```
extract_start = physical_start_page_of_ch_N
extract_end   = physical_start_page_of_ch_{N+1} - 1
```

For the **last chapter** (no next chapter to anchor):

```
extract_start = physical_start_page_of_last_chapter
extract_end   = physical_start_page_of_back_matter - 1
# OR: extract_end = total_pages (if back matter is inseparable)
```

For **appendices/references/index**:

```
extract_start = physical_start_page
extract_end   = physical_start_page_of_next_section - 1
# OR: extract_end = total_pdf_pages (for the last section)
```

#### Step C — Validate Extraction Completeness

After running MinerU, **immediately validate** that the extracted content is complete:

```python
# Pseudo-code: check for chapter-ending markers
extracted_text = read("source_final/chapter_N.md")
last_50_lines = extracted_text[-50:]

# Positive indicators (chapter IS complete):
HAS_SUMMARY     = "สรุป" in last_50_lines          # Thai: summary
HAS_EXERCISES   = "แบบฝึกหัด" in last_50_lines     # Thai: exercises
HAS_SECTION_END = any(marker in last_50_lines for marker in 
    ["สรุปท้ายบท", "แบบฝึกหัดท้ายบท", "习题", "本章小结"])

# Negative indicators (chapter may be incomplete):
HAS_NEXT_CHAPTER  = "บทที่" in last_50_lines       # Thai: next chapter heading
ENDS_MID_SENTENCE = extracted_text.strip().endswith(("-", "=", "$$"))  
NO_ENDING_MARKER  = not HAS_SUMMARY and not HAS_EXERCISES

if NO_ENDING_MARKER and not HAS_NEXT_CHAPTER:
    # SUSPICIOUS: no summary and no next chapter heading
    # Likely the page range was too narrow
    WARN("Chapter N may be incomplete. Extend range and re-extract.")
    
if HAS_NEXT_CHAPTER:
    # CONFIRMED: got content from the next chapter
    # Page range was too wide — that's OK, we can trim
    NOTE("Chapter N overlaps with Ch{N+1}. Will split.")
```

**Repeat until the validation passes.** This is a mandatory gate — do NOT proceed to translation until every chapter passes.

### 1.3 The 5-Minute Safety Check (Before Translation)

After ALL chapters are extracted, do this once:

```bash
for f in source_final/*.md; do
    name=$(basename "$f")
    lines=$(wc -l < "$f")
    last_10=$(tail -10 "$f")
    echo "=== $name ($lines lines) ==="
    # Check for summary/exercises in last lines
    echo "$last_10" | grep -E "สรุป|แบบฝึกหัด|习题|小结|练习" && echo "  ✅ Has ending marker" || echo "  ⚠️  NO ending marker — check completeness"
    echo ""
done
```

Any file missing an ending marker is SUSPICIOUS. Investigate before translating.

### 1.4 Common Patterns by Chapter Position

| Position | Typical End Marker | Risk Level |
|----------|-------------------|------------|
| **First half chapters** | Summary + Exercises | Low — usually within range |
| **Penultimate chapter** | Summary + Exercises + transition to last topic | Medium |
| **Last chapter** | Summary + Appendix/References start | **HIGH** — most likely to be truncated |
| **Appendix** | End of content + blank page | Low |
| **References** | Last reference entry | Low |

---

## 2. Phase 1: Targeted Extraction (MinerU) — Tool Usage Guide

### 2.0 Pre-Extraction: PDF Annotation Sanitization (MANDATORY for hand-annotated PDFs)

**Symptom**: If the PDF carries an **annotation layer** (notes the reader added in a PDF editor), MinerU rasterizes the annotation appearances into the page image. Comment boxes (`/FreeText`) look like small bordered boxes, so the layout model classifies them as **figures** — the note text is NOT extracted as text, and instead a junk JPEG appears in `images/` (plus a stray `![](...)` reference in the markdown). Highlights (`/Highlight`) add colour overlays that also lower OCR contrast. This is the #1 cause of "spurious tiny images" and "missing notes" on books that were hand-annotated.

**Step 1 — Detect the annotation layer:**

```python
from pypdf import PdfReader
r = PdfReader("book.pdf")
kinds = {}
for pg in r.pages:
    a = pg.get("/Annots")
    if not a:
        continue
    for an in a.get_object():
        st = str(an.get_object().get("/Subtype"))
        kinds[st] = kinds.get(st, 0) + 1
print(kinds)   # e.g. {'/Link': 710, '/Highlight': 460, '/FreeText': 25, '/Popup': 76}
```

- `/FreeText` = text note boxes → junk figures. **Any count > 0 means you MUST sanitize.**
- `/Highlight`, `/Underline`, `/StrikeOut`, `/Squiggly`, `/Stamp`, `/Ink`, `/Popup` = reader markup.
- `/Link` = usually harmless TOC links (safe to strip too).

**Step 2 — Strip the annotation layer from a WORKING COPY (never modify the original PDF):**

```python
from pypdf import PdfReader, PdfWriter
r = PdfReader("book.pdf"); w = PdfWriter()
for pg in r.pages:
    if "/Annots" in pg:
        del pg["/Annots"]
    w.add_page(pg)
with open("book_clean.pdf", "wb") as f:
    w.write(f)

# verify: page count preserved, zero annots remain
r2 = PdfReader("book_clean.pdf")
assert len(r2.pages) == len(r.pages)
assert not any("/Annots" in pg for pg in r2.pages)
```

Then run MinerU on `book_clean.pdf`. Verified on an annotated 701-page book (3-page test range): **3 images before (2 real figures + 1 note box) → 2 images after (the two figures survive; the `/FreeText` box is gone and its note text is correctly absent, since reader annotations are NOT original book content).**

**Step 3 - If the annotations are study notes you WANT to keep**: do NOT rely on OCR of the boxes. Export them from the annotation layer into a side file keyed by page, then merge deliberately:

```python
for i, pg in enumerate(PdfReader("book.pdf").pages, 1):
    a = pg.get("/Annots")
    if not a: continue
    for an in a.get_object():
        o = an.get_object()
        if str(o.get("/Subtype")) == "/FreeText":
            print(i, repr(str(o.get("/Contents"))))
```

**Repairing an already-extracted book** (annotations already became images): locate the junk figures by size (note boxes are tiny — often < 150 px on a side, or wide-and-short strips) and cross-check them against the `/FreeText`/`/Highlight` rects, then delete the image and its `![](...)` reference, or re-extract that page range from the sanitized copy.

### 2.1 MinerU Basic Command

```bash
mineru --lang <language_code> --page-range <start-end> "input.pdf"
```

| Parameter | Value | Note |
|-----------|-------|------|
| `--lang` | `th` (Thai), `en`, `zh`, etc. | Set this to the PDF's language. Wrong language = bad OCR |
| `--page-range` | `31-62` | Extracts only those pages. Omit = whole PDF |
| Input PDF | path to PDF | Use absolute or relative path |

### 2.2 Understanding MinerU's Output Structure

After running, MinerU creates a nested output directory. **The output location depends on the PDF filename**:

```
<repo-root>/
└── <PDF-filename>/          # Named after the PDF file
    └── auto/ 或 hybrid_auto/  # Extraction mode directory
        ├── <PDF-filename>.md           # ← THE MAIN OUTPUT FILE
        ├── <PDF-filename>_layout.pdf   # Layout debug PDF (ignore)
        ├── <PDF-filename>_middle.json  # Middle format JSON (ignore)
        ├── <PDF-filename>_model.json   # Model metadata (ignore)
        ├── <PDF-filename>_content_list.json     # Content structure (useful for verification)
        ├── <PDF-filename>_content_list_v2.json  # Content structure v2
        └── images/
            ├── abc123.jpg              # ← ALL extracted images
            ├── def456.jpg
            └── ...
```

**Key actions after extraction:**

```bash
# 1. Find the output directory (it's named after the PDF file)
ls -d "HDD3-Volume Ill - Advanced Receiver Design"/

# 2. Locate the main markdown file inside
find "HDD3-Volume Ill - Advanced Receiver Design" -name "*.md" -not -path "*/_layout/*"

# 3. Copy to source_final/
cp "HDD3-Volume Ill - Advanced Receiver Design/auto/HDD3-Volume Ill - Advanced Receiver Design.md" \
   source_final/chapter_8.md

# 4. Copy images to repo images/
mkdir -p images/chapter_8/
cp "HDD3-Volume Ill - Advanced Receiver Design/auto/images/"*.jpg images/chapter_8/
```

> **⚠️ Don't search blindly.** Know the pattern: `<PDF-name>/<mode>/<PDF-name>.md`. The mode directory is typically `auto/` or `hybrid_auto/`.

### 2.3 MinerU Output Gotchas

| Issue | Example | Mitigation |
|-------|---------|------------|
| **Spurious digits** | "อินพุต61 $a_k$" (61 is junk) | `61` is an OCR artifact between Thai text and LaTeX; ignore during translation |
| **Character confusion** | ร vs ฯ, ซ vs ศ | Common Thai OCR errors; context usually resolves them |
| **Broken equations** | Random variables mixed into Thai text | The equation may be corrupted; preserve as-is in source, note in translation |
| **LaTeX delimiter splitting** | `$$` split across paragraphs | MinerU may break `$$...$$` across lines; manually rejoin if needed |
| **Missing last page(s)** | Chapter ends abruptly | Page range too narrow — extend and re-extract (see §1.2) |
| **Image duplication** | Same image extracted multiple times | Deduplication by SHA hash is reliable; duplicates have identical filenames |
| **Annotation box extracted as a "figure"** | Tiny JPEG that is a `/FreeText` note box (e.g. a yellow box with a note) | Strip `/Annots` from a working copy BEFORE MinerU (see §2.0) |
| **Highlight overlay degrades OCR** | Text under a `/Highlight` comes out garbled | Strip `/Annots` (highlights included) before extraction |
| **In-figure annotation read as body text** | A short line (sub-caption, curve name, source note) sits immediately above an `![](...)` figure | It is figure-internal text, not prose — demote to a centered small block in post-processing (see §7 "figure annotation" note), do NOT translate as a paragraph |

### 2.4 MinerU's Image Output Specifics

MinerU extracts every figure/equation as a separate JPEG file named by its SHA-256 hash:

```
images/cff3b326ef30d5c56b89ccdb7e5d2603ec3715db50fc378d37b0cabaa3afc871.jpg
```

The extracted Markdown references them as:
```markdown
![](images/cff3b326ef30d5c56b89ccdb7e5d2603ec3715db50fc378d37b0cabaa3afc871.jpg)
```

After moving to `images/chapter_N/`, the path must be updated to `../images/chapter_N/hash.jpg`.

> **⚠️ MinerU SHA hash mismatch bug**: Sometimes the filename in the `images/` directory differs from the reference in the `.md` file by 1-3 characters at the end. This is a MinerU bug. When "missing image" is reported, DON'T assume it's a real missing image — compare the actual directory listing with the reference to spot the typo.

### 2.5 Batch Image Path Fix

After ALL chapters are extracted (NOT after each one), fix image paths in bulk:

```python
import os, re

base = '/path/to/project'
for lang_dir in ['source_final', 'chinese_final']:
    d = os.path.join(base, lang_dir)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.md'):
            continue
        fp = os.path.join(d, fn)
        with open(fp, 'r') as f:
            content = f.read()
        def fix_path(m):
            full = m.group(1)
            if full.startswith('../'):
                return m.group(0)
            return f"![](../{full})"
        new_content = re.sub(r'!\[\]\((images/[^)]+)\)', fix_path, content)
        if new_content != content:
            with open(fp, 'w') as f:
                f.write(new_content)
```

> **Why `../images/`?** From `source_final/chapter_N.md`, `images/foo.jpg` resolves to `source_final/images/foo.jpg` which doesn't exist. `../images/foo.jpg` resolves to `images/foo.jpg` at repo root.

### 2.6 Image Verification (Mandatory — Do NOT Skip)

After fixing paths, verify EVERY image reference exists on disk:

```python
import os, re
base = '/path/to/project'
missing = []
total = 0
for lang_dir in ['source_final', 'chinese_final']:
    d = os.path.join(base, lang_dir)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.md'):
            continue
        fp = os.path.join(d, fn)
        with open(fp, 'r') as f:
            content = f.read()
        refs = re.findall(r'!\[\]\(([^)]+)\)', content)
        total += len(refs)
        for ref in refs:
            if ref.startswith('../'):
                img_path = os.path.normpath(os.path.join(d, ref))
            else:
                img_path = os.path.join(base, ref)
            if not os.path.exists(img_path):
                missing.append((lang_dir, fn, ref, img_path))

if missing:
    print(f"MISSING: {len(missing)} of {total} images")
    for m in missing:
        print(f"  {m[0]}/{m[1]}: {m[2]}")
        # Try to find the actual file (SHA hash might differ slightly)
        dir_part = os.path.dirname(m[3])
        if os.path.isdir(dir_part):
            for fname in sorted(os.listdir(dir_part))[:5]:
                print(f"    Nearby: {fname}")
else:
    print(f"ALL {total} image references verified! 0 missing.")
```

### 2.7 Clean Raw Output

After copying the clean files and images, **delete** MinerU's output directories:

```bash
rm -rf "HDD3-Volume Ill - Advanced Receiver Design"/
rm -rf output_chapter_*/
rm -f calibration*.txt pages_*.txt toc_preview.txt
rm -rf mineru_test/
```

> These intermediate artifacts **must not** be committed. MinerU's output directory alone can contain thousands of files (one JPEG per equation/figure).

### 2.8 Final Deliverables

After all chapters are extracted, the directories should contain **only**:

```
source_final/          # Clean Thai Markdown
├── chapter_1.md
├── chapter_2.md
├── ...
├── appendix_a.md
├── appendix_b.md
├── References.md
└── index.md

chinese_final/         # Chinese translations
├── chapter_1.md
├── chapter_2.md
├── ...
├── appendix_a.md
└── References.md

images/                # Book images
├── chapter_1/
├── chapter_2/
├── ...
└── appendix/
```

---

## 3. Git Hygiene

### 3.1 The Problem

When the repo was initialized without `.gitignore`, or MinerU artifacts were accidentally committed, the git history contains hundreds of unwanted files.

### 3.2 If Junk Was Already Committed (Local Only)

Use `git rm --cached` to stop tracking unwanted files:

```bash
# List all tracked files
git ls-files

# Remove unwanted tracked files
git rm --cached .DS_Store
git rm --cached -r .omo/
git rm --cached -r .opencode/
git rm --cached AGENTS.md "original.pdf" extract_book.sh extraction.log
git rm --cached -r mineru_test/

# Update .gitignore to prevent re-add
# Then commit
git commit -m "Clean: remove non-project files from tracking"
```

### 3.3 If Remote Already Has Junk — Orphan Branch Reset (ONLY WHEN A REMOTE EXISTS)

> **Applies only to projects with a configured remote.** Many translation projects are **local-only** (no remote, no push). Check first: `git remote -v`. If it prints nothing, SKIP this entire section — just keep clean local history with §3.2.

```bash
# Preconditions: `git remote -v` is non-empty AND `git ls-files` shows only the intended files.
# Create orphan branch (no shared history with main)
git checkout --orphan clean-main

# Clear the staging area
git read-tree --empty

# Add ONLY the clean deliverables (adjust for multi-book layout)
git add .gitignore README.md chinese_final/ source_final/ images/

# Commit
git commit -m "Initial commit: clean repo"

# Force push (destructive — see warning below)
git push -f origin clean-main:main

# Local cleanup
git branch -D main
git branch -m clean-main main
```

### 3.4 Verification

```bash
# Verify only the intended files are tracked
git ls-files

# Single-book: should output NOTHING
git ls-files | grep -v '^chinese_final/' | grep -v '^source_final/' | grep -v '^images/' | grep -v '^README.md$' | grep -v '^\.gitignore$'

# Multi-book: should output NOTHING
git ls-files | grep -vE '^[^/]+/(source_final|chinese_final|images)/' | grep -vE '^[^/]+/README\.md$' | grep -vE '^(README\.md|\.gitignore)$'
```

> **⚠️ Force push warning**: `git push --force` overwrites remote history and is **irreversible for collaborators**. Only run it after (a) a remote actually exists, (b) `git ls-files` confirms the local state, and (c) the user has approved. Never run it as a reflexive final step.

---

## 4. Phase 2: Recursive Atomic Translation Loop

### 4.1 State Tracking

Use `.omo/progress.md` locally but **do NOT track it** in the repo.

### 4.2 The Atomic Loop Sequence

**Step 1: Grounding** — Read `.omo/progress.md` + last lines of `chinese_final/chapter_N.md` to find the resume point.

**Step 2: Read Source** — Read the next section from `source_final/chapter_N.md` (use `offset` + `limit` for a small block, ~30-50 lines).

**Step 3: Translate** — Convert the source language to Chinese while preserving:
- LaTeX equations **verbatim** (`$$...$$`, `$...$`)
- Heading levels (`#`, `##`, `###`)
- Lists and table structures
- Image references (`![](../images/chapter_N/hash.jpg)`) — keep path as-is

**Step 4: Append** — Append translated content to `chinese_final/chapter_N.md`. **Never overwrite the file.**

**Step 5: Update Progress** — Update `.omo/progress.md` with the new pointer position.

**Step 6: Commit** — `git add chinese_final/chapter_N.md && git commit -m "Translate ch.N sec.X"` (stage the ONE file explicitly; never `git add -A`, which can sweep in untracked junk if `.gitignore` is imperfect).

### 4.3 Section Size Guidelines

| Content Type | Max Lines | Reason |
|---|---|---|
| Prose paragraphs | 40 lines | Prevents context overflow |
| Equation-heavy | 20 lines | Maintains LaTeX fidelity |
| Tables | 15 lines | Complex structure |

### 4.4 Translation QA Gates (C1–C10) — run before every install/commit

Append-translating whole chapters drifts silently. These ten checks are **mandatory** and cheap; a failure means DO NOT install/commit until fixed. Build a `final.md` the same way you build the chapter (one translated line replaces its source line, **1:1, same line count**), then run the gates against `source` vs the built output.

| # | Gate | Rule |
|---|------|------|
| C1 | Line count | `src_lines == zh_lines` (1:1 mapping — a translation never adds/removes lines) |
| C2 | No trailing newline | output does NOT end with `\n` (matches source convention) |
| C3 | `$` total & per-line | total `$` equal AND every line's `$` count equal |
| C4 | Math-token order | the ordered list of `$...$` spans is byte-identical, in order, line by line |
| C5 | Verbatim lines | lines NOT marked as translated are byte-identical (refs, authors, bios, display math, IMG, dividers) |
| C6 | CJK coverage | every translated line contains CJK — except an explicit whitelist (bare eq numbers, `(39.17)`) |
| C7 | Control chars | multiset of `ord<32` exactly matches source (preserve `\x07` etc. — see below) |
| C8 | Trailing spaces | per-line trailing-space count matches source (IMG lines often have exactly 2) |
| C9 | No literal escapes | after build, no literal `\xNN` remains (tokens were patched to real chars) |
| C10 | Special chars | per-codepoint multiset of non-ASCII/non-CJK/non-`、` (outside `$`) matches source, minus an explicit W-whitelist |

**The placeholder method (makes C4/C5 trivial):** in your working translation data, replace the i-th `$...$` span of a source line with `⟦i⟧`. Store math **outside** the translated text. At build time, substitute each `⟦i⟧` back with its exact original span. This guarantees byte-exact equations and catches accidental reordering (placeholder indices must appear as `0,1,2,…` in text order).

**Control characters:** MinerU sometimes emits raw control chars (e.g. a stray `U+0007` inside an equation). Do NOT paste them into your data file. Write the literal token `\x07` as text; the builder patches it to the real char; C7 verifies the count, C9 verifies the token is gone.

**Specials & the W-whitelist:** characters like `α ⊕ – — ’ “ ” × · − →` live **outside** `$` spans and are easy to drop or "normalize". C10 compares the exact per-codepoint multiset. If a translation legitimately drops a character (e.g. an English possessive `’` becomes nothing in Chinese), record it in the whitelist `W` keyed by line number — do not silently "fix" the source.

**House style (all enforced by the gates):** ASCII punctuation only; sentence ends with `.` not `。`; `、` (U+3001) is allowed; captions rendered as `图 N.N`; `## References` → `## 参考文献`, `## Abstract` → `## 摘要`; references / author lines / bios / IMG / display math kept verbatim.

> Minimal verifier layout: keep `targets` (the line numbers you translated) in one file, and assert `set(entries) == set(targets)`. C5 is then "every non-target line is identical".

**A ready-to-run implementation ships with this skill:** `scripts/verify_chapter.py` (stdlib only). It runs all ten gates and exits non-zero on failure:

```bash
python3 scripts/verify_chapter.py --src source_final/chapter_8.md --zh chinese_final/chapter_8.md \
    --targets targets.txt --c6wl 225,227 --w10 w10.json
```

Omit `--targets` to auto-skip the strict C5/C6 form when you did not record target lines.

---

## 5. Phase 3: README & Finalization

### 5.1 Bilingual README

Generate a README with both Chinese and English sections:

```markdown
## 中文版

### 翻译状态

| 章节 | 源文件 | 中文翻译 | 状态 |
|------|--------|----------|------|
| **Ch1** 概述 | [source](source_final/chapter_1.md) | [中文](chinese_final/chapter_1.md) | ✓ |

## English Version

### Translation Status

| Chapter | Source | Chinese | Status |
|---------|--------|---------|--------|
| **Ch1** Introduction | [source](source_final/chapter_1.md) | [chinese](chinese_final/chapter_1.md) | ✓ |
```

- Each chapter row links to both source and translation files
- Include stats: PDF pages, total images, completeness percentage
- Mark untranslated sections clearly (✗)

### 5.2 Copyright & License

For a derivative translation work:
- **No standard OSS license** (MIT/GPL/Apache) — those imply you own the rights
- Keep a plain-English copyright notice: "Original work © [Author]. This is an unofficial translation."
- A CC BY-NC-ND 4.0 notice can be added for the translation portion
- Do NOT claim ownership of the original content

### 5.3 Final Commit (and Optional Push)

```bash
# Commit the deliverables. Stage files EXPLICITLY — never `git add -A`/`git add .`
# (that can sweep in untracked junk if .gitignore is imperfect).
git add .gitignore README.md chinese_final/ source_final/ images/
git commit -m "Final: complete book translation"
```

**Push is OPTIONAL and only for projects with a remote.** If `git remote -v` is empty (the common local-only case), you are done — do NOT add a remote, do NOT force-push. If a remote exists and its history is dirty, see §3.3 (with its preconditions and warning) — `--force` is a last resort, never a default final step.

---

## 6. Image Path Convention (CRITICAL)

All images must use paths relative to the Markdown file's directory:

```markdown
<!-- In source_final/chapter_N.md or chinese_final/chapter_N.md -->
![](../images/chapter_N/hash.jpg)
```

**Why `../images/` and NOT `images/` or `../source_final/images/`:**

| Path | Resolves to (from source_final/) | Exists? |
|------|----------------------------------|---------|
| `images/foo.jpg` | `source_final/images/foo.jpg` | ❌ |
| `../source_final/images/foo.jpg` | `source_final/../source_final/...` | ❌ |
| `../images/foo.jpg` | `images/foo.jpg` | ✅ |

The images directory lives at project root, NOT under source_final/.

### Batch Path Fix

When moving images from MinerU output, always fix ALL chapter files at once with a regex script. Never edit image paths manually.

### Verification

After any path change, run a complete verification:
1. Extract all `![](...)` references from all `.md` files
2. Check each resolved path exists on disk
3. Fix any mismatches (common: SHA hash typos from MinerU)

---

## 7. Common Mistakes & Anti-Patterns

### ❌ NEVER Do These

1. **Push without verifying images** → Always run the full reference check first
2. **Trust automated page ranges** → Verify by opening the PDF
3. **Edit image paths manually** → Use batch regex script
4. **Commit MinerU artifacts** (output_*, calibration*, pages_*, mineru_test/) → Delete before staging
5. **Track .DS_Store files** → Add to .gitignore immediately
6. **Include original PDF, scripts, logs in repo** → Track ONLY source/text output
7. **Include working directories (.omo/, .opencode/, AGENTS.md)** → These are local project files
8. **Hardcode translation model name** → Don't specify unless confirmed by the user
9. **Use `git push --force` without verifying local state first** → Check `git ls-files`
10. **Assume .gitignore retroactively untracks files** → Use `git rm --cached`
11. **Extract a hand-annotated PDF without stripping its annotation layer first** → `/FreeText` note boxes become junk "figures" and the note text is silently lost (§2.0)
12. **Modify the original PDF** → Always sanitize into a separate `book_clean.pdf` working copy

### ✅ Always Do These

1. **Set up .gitignore before first commit** — deny-by-default pattern
2. **Verify ALL image references** after any path changes
3. **Batch-fix image paths** with Python regex across all files
4. **Use bilingual README** with file links for every chapter
5. **Push with --force when cleaning remote** — after verifying local state
6. **Remove from tracking**: `git rm --cached` files that were committed before gitignore
7. **Keep images at repo root** (`images/`), not under source directories
8. **Check PDF page ranges manually** before running full extraction
9. **Append to translation files** — never overwrite
10. **Commit after each atomic translation section**
11. **Count `/Annots` subtypes with pypdf before extraction** — if any `/FreeText` exists, sanitize first (§2.0)

### Figure-Internal Text (Sub-Captions, Curve Names, Source Notes)

Separate from reader annotations (§2.0) is **text that is part of the figure itself** — OCR often lifts a short line out of the image and places it on the line immediately above the `![](...)` reference. It is not prose; do not translate it as a paragraph. Demote it to a centered small block in post-processing, e.g.:

```python
def fix_figure_annotations(text):
    """Short line (<40 chars, no sentence-ending punctuation, not a numbered
    caption/heading) placed immediately above an image -> centered small block."""
    def _is_annot(s):
        if not s or len(s) > 40 or re.search(r"[。;；]", s): return False
        if re.match(r"^(图|表|定理|性质|定义|证明|算法|引理|推论)\s*\d", s): return False
        return not re.match(r"^\d+\.\d+", s)
    lines = text.splitlines(); out = []
    for i, l in enumerate(lines):
        s = l.strip()
        if i + 1 < len(lines) and lines[i+1].strip().startswith("![") \
           and _is_annot(s) and not s.startswith(("!", "|", "-", "*", "#", "$")):
            out.append("\\begin{center}\n\\small " + s + "\n\\end{center}")
        else:
            out.append(l)
    return "\n".join(out)
```

Guard it: re-read every flagged line against the figure before trusting the heuristic — a genuine short prose line adjacent to a figure must NOT be demoted.

---

## 8. Appendices & Back Matter

### Handling Appendices

- Appendices are often at the END of the last chapter's PDF page range
- Extract them separately or include them in the last chapter's range
- Create independent files: `appendix_a.md`, `appendix_b.md`, etc.
- References/Index may also be inline — check content carefully

### Section Dividers (single-page "Part I / Section II" pages)

Multi-part books have thin **divider pages** that carry no chapter content — only a part/section title (often with that section's Contents listing on the same or next page).

- Do NOT create a source file for a divider; **skip it** (record its title for the README).
- A divider page can double as page 1 of the section's Contents listing. Verify: if `pdftotext <page>` yields only a title + a list of chapter names/authors, it is a divider, not chapter text.
- Keep a "skipped dividers" table in the README so no page silently vanishes.

### Boundary-Gap / Folded Contents Pages (CRITICAL)

The range rule in §1.1 (`ch_N` = start of N .. start-1 of N+1) can leave a **gap page** between a divider and the chapter start, or between chapters. Before assigning ranges:

```bash
# does the gap page contain real text or is it blank?
pdftotext -f <gap_page> -l <gap_page> "book.pdf" - | head
```

- **Blank gap page** → harmless; ignore (do not create a file).
- **Gap page with text** (a section-Contents continuation, "II-2", running header + chapter list + copyright line) → **FOLD it into the following chapter**: extend that chapter's range to start at the gap page (`ch_N = [gap_page, next_start-1]`). Record the fold verdict in the page map.

Then run a coverage check: every content page is covered by exactly one file, and the only uncovered pages are the skipped dividers and true blanks. This is the same discipline as §1.2 — do it programmatically, not by eye.

### References

- English-language references need NO translation (keep verbatim).
- **Per-chapter inline References**: many chapters end with their own References section inside the chapter file. Keep that section English and translate the rest of the chapter; only split it into a separate file when the book has a single global bibliography.
- Mark as "✓ (English)" in the status table.
- Refs are almost always on a regular cadence (e.g. every even line L272…L362); the reference block is a natural **verbatim (C5) region** — never translate or renumber it.

### Index

- Can be left untranslated if purely terminological
- Mark as "✗" in status table with clear note

---

## 9. HDD3 Book Conversion Checklist (Example)

- [ ] Pre-flight: `git remote -v` — note whether the project is local-only (default) or has a remote
- [ ] Annotation check BEFORE extraction: count `/Annots` subtypes; sanitize `/FreeText`/`/Highlight` into a working copy (§2.0)
- [ ] PDF extraction complete (verify page-by-page); no annotation-box "figures" in `images/`
- [ ] Page map built with next-chapter anchoring; gaps classified blank vs fold (§1.2, §8)
- [ ] Section dividers skipped and listed in README
- [ ] Image paths fixed (referenced from repo root `images/`)
- [ ] All image references verified against actual files (0 missing)
- [ ] Each chapter passes the QA gates C1–C10 (§4.4) before install/commit
- [ ] Bilingual README with per-chapter file links
- [ ] .gitignore deny-by-default, no extra files tracked
- [ ] Translation model attribution confirmed with user
- [ ] Copyright notice in README
- [ ] Commits stage files explicitly (no `git add -A`)
- [ ] Push ONLY if a remote exists; never force-push as a default final step (§5.3)
