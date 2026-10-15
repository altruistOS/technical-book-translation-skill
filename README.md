<div align="center">

# Technical Book Translation Skill

> 把技术书 PDF 变成**公式零误差**的中英对照 Markdown：MinerU 抽取 → 原子级翻译 → C1–C10 质检。

[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)
[![Codex](https://img.shields.io/badge/Codex-Compatible-blueviolet)](#安装)
[![OpenCode](https://img.shields.io/badge/opencode-Compatible-8A2BE2)](#安装)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

**一个技能，一条流水线：从满是批注的 PDF，到可发布的翻译仓库。**

[功能特性](#功能特性) · [安装](#安装) · [快速开始](#快速开始) · [质检关卡](#质检关卡-c1c10) · [项目结构](#项目结构)

</div>

---

## 为什么需要它

把一本技术书翻成 Markdown，看起来只是"OCR + 翻译"，实际处处是坑：

- **手写批注的 PDF**：读者留下的注释框（`/FreeText`）会被 MinerU 当成**插图**，于是一张垃圾小图混进 `images/`，而注释文字却凭空消失。
- **页码算错**：按目录页范围抽取，章节结尾（小结 / 习题）被整段截掉 —— 几乎每个项目都会踩。
- **公式走样**：翻译时手滑改动一个 `$...$`，整条公式就错了。
- **静默漂移**：逐段追加翻译，中文行数、行尾空格、控制字符慢慢和原文对不上，无人察觉。

本 Skill 用**一套可复现的流水线与十道自动质检**，把上面每一条都变成"跑一遍脚本就能发现"的问题。

---

## 功能特性

| 能力 | 说明 |
|------|------|
| **批注净化** | 抽取前用 `pypdf` 统计 `/Annots` 子类型；凡有 `/FreeText` 即在工作副本上剥离，杜绝"注释框变插图"（§2.0） |
| **页码锚定** | 章节范围以**下一章起始页**为锚（`ch_N = start_N .. start_{N+1}-1`），不信任目录页；抽取后自动校验结尾标记 |
| **缺口分类** | 章节间的空白页 / 折叠目录页，用 `pdftotext` 逐页判定：空白忽略，有正文则并入下一章 |
| **图片治理** | 批量修正为 `../images/chapter_N/hash.jpg`，并强制校验**每一处引用都存在**（0 missing） |
| **原子级翻译** | 逐段翻译、**追加写入**、不覆盖；翻译文本与公式/图片/参考文献分离管理 |
| **C1–C10 质检** | 行数、尾换行、`$` 计数、公式顺序、逐字保留、CJK 覆盖、控制字符、行尾空格、转义残留、特殊字符多重集 —— 十项全过才允许提交 |
| **可运行校验器** | 随技能附带 `scripts/verify_chapter.py`（纯标准库），一条命令跑完全部关卡 |

---

## 安装

把整个仓库（或至少 `SKILL.md` + `scripts/`）放到目标 Agent 的技能目录，使 `SKILL.md` 位于技能文件夹根级。

```bash
git clone https://github.com/altruistOS/technical-book-translation-skill.git
```

| Agent | 技能目录 |
|-------|----------|
| **Codex** | `~/.codex/skills/technical-book-translation/` |
| **OpenCode** | `~/.config/opencode/skills/technical-book-translation/` |
| **Claude Code** | `<项目>/.claude/skills/technical-book-translation/` |
| **DSH Desktop / DeepSeek Harness** | `<userData>/harness/skills/technical-book-translation/`（二者均从 Codex 技能目录同步） |

---

## 快速开始

```bash
# 0) 仓库与 .gitignore（deny-by-default，见 SKILL.md §0.2）
git init

# 1) 抽取前：检测并净化批注层（工作副本，绝不动原件）
python - <<'PY'
from pypdf import PdfReader, PdfWriter
r = PdfReader("book.pdf"); w = PdfWriter()
for pg in r.pages:
    if "/Annots" in pg: del pg["/Annots"]
    w.add_page(pg)
with open("book_clean.pdf", "wb") as f: w.write(f)
PY

# 2) MinerU 按页范围抽取
mineru --lang en --page-range 31-62 "book_clean.pdf"

# 3) 逐段翻译并追加写入 chinese_final/chapter_N.md（不覆盖）

# 4) 每个章节提交前跑质检
python3 scripts/verify_chapter.py \
    --src source_final/chapter_8.md \
    --zh  chinese_final/chapter_8.md \
    --targets targets.txt --c6wl 225,227 --w10 w10.json
```

`scripts/verify_chapter.py` 全部通过时退出码为 `0`；任一关卡失败即非零退出并打印差异。省略 `--targets` 时会自动跳过严格的 C5/C6 形式。

---

## 质检关卡 C1–C10

| # | 关卡 | 规则 |
|---|------|------|
| C1 | 行数 | `src_lines == zh_lines`（翻译不增删行） |
| C2 | 尾换行 | 输出**不以** `\n` 结尾 |
| C3 | `$` 计数 | `$` 总数相等，且**逐行**相等 |
| C4 | 公式顺序 | `$...$` 片段按行逐字节一致且顺序一致 |
| C5 | 逐字保留 | 非翻译行（参考文献/作者/公式/图片/分隔）逐字节相同 |
| C6 | CJK 覆盖 | 每个翻译行都含 CJK（裸公式号等走白名单） |
| C7 | 控制字符 | `ord<32` 的多重集与原文完全一致 |
| C8 | 行尾空格 | 逐行行尾空格数与原文一致 |
| C9 | 转义残留 | 构建后不残留字面 `\xNN` |
| C10 | 特殊字符 | 非 ASCII/非 CJK 字符（`$` 外）的多重集与原文一致，减去显式 W 白名单 |

> 细节（占位符 `⟦i⟧` 方法、`\xNN` 令牌、W 白名单、排版约定）见 [`SKILL.md`](SKILL.md) §4.4。

---

## 项目结构

```
technical-book-translation-skill/
├── SKILL.md                  # 完整流水线（生产 → 抽取 → 翻译 → 质检 → 交付）
└── scripts/
    └── verify_chapter.py     # C1–C10 校验器（纯标准库）
```

翻译产物仓库（本技能产出的目标物）布局：

```
<book-repo>/
├── source_final/     # 抽取后的原文 Markdown
├── chinese_final/    # 中文翻译
├── images/           # 全部图片（chapter_N/ …）
└── README.md         # 中英双语翻译状态表
```

---

## 说明

- 本仓库是**翻译流程技能**，不包含任何书籍的原作内容。
- 使用本技能产出的**译文**属演绎作品：请在制品 README 中保留原作版权声明，不要对原文主张所有权（见 `SKILL.md` §5.2）。
- 本仓库暂未附加开源许可证。

---

## English

**Technical Book Translation Skill** turns a technical PDF into a faithful, equation-accurate bilingual Markdown edition. It covers the full pipeline — MinerU/OCR extraction, annotation sanitization for hand-annotated PDFs, chapter page-range mapping, image handling, atomic append-only translation, and a ten-gate QA verifier — with concrete failure modes and their fixes.

Highlights:

- **Annotation sanitization (§2.0)** — `/FreeText` note boxes get rasterized and misclassified as figures; detect and strip the annotation layer from a working copy before extraction.
- **Page-range anchoring** — derive each chapter's range from the *next* chapter's start, then validate for end markers (summary/exercises).
- **Atomic translation** — append-only, one translated line per source line; equations/refs/images kept verbatim.
- **C1–C10 QA gates** — line count, trailing newline, `$` counts, math order, verbatim lines, CJK coverage, control chars, trailing spaces, escape residue, special-char multisets — implemented in [`scripts/verify_chapter.py`](scripts/verify_chapter.py).

```bash
python3 scripts/verify_chapter.py --src source_final/chapter_8.md \
    --zh chinese_final/chapter_8.md --targets targets.txt
```

See [`SKILL.md`](SKILL.md) for the full workflow.
