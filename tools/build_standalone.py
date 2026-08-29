#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
為每個 skill 產生 STANDALONE.md：SKILL.md（去除 YAML frontmatter）＋ references/ ＋ assets/。

    python tools/build_standalone.py            # 產生／更新全部 skill 的 STANDALONE.md
    python tools/build_standalone.py --check    # 只檢查是否為最新（CI 用，不寫檔）

STANDALONE.md 供 ChatGPT Knowledge / Claude Project / Gemini Gems 上傳使用，
內容必須與各分檔一致。改動任何分檔後執行本腳本重新產生，不要手動編輯 STANDALONE.md。
兩個 skill 各有一份，成對上傳；只上傳其中一份時，另一份的參考檔會缺席。
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

TITLES = {
    "tw-gov-it-docs": "台灣政府資訊系統委外文件撰寫（完整版）",
    "tw-gov-it-review": "台灣政府資訊系統委外文件審查（完整版）",
    "tw-gov-ta-docs": "顧問協辦工作說明書撰寫（完整版）",
}

HEADER = """# {title}

> 單檔完整版，供 ChatGPT Knowledge / Claude Project / Gemini Gems 上傳使用。
> 本檔由 `tools/build_standalone.py` 自動產生，請勿手動編輯；要修改請改各分檔後重新產生。
>
> **路徑對照**：本檔已包含本 skill 全部 `references/`{assets_note} 的內容。內文提到
> 「讀取 `references/○○.md`」時，請直接參照本檔下方對應的同名章節，不需要（也無法）另外開檔。
> 內文提到 `scripts/` 的腳本、以及 `../` 開頭指向另一個 skill 的路徑，在單檔版中不存在；
> 需要那些內容時請一併上傳另一份 STANDALONE.md。
"""

ASSETS_INTRO = """# 附錄：文件骨架

以下為各文件的空白骨架。撰寫時直接在骨架上填內容，不要自行重編章節。
"""


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4:].lstrip("\n")


def build(skill_dir: Path) -> str:
    references = sorted((skill_dir / "references").glob("*.md"))
    assets = sorted((skill_dir / "assets").glob("*.md"))
    header = HEADER.format(
        title=TITLES.get(skill_dir.name, skill_dir.name),
        assets_note=" 與 `assets/`" if assets else "",
    )

    parts = [header,
             strip_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8")).rstrip()]
    parts += [f.read_text(encoding="utf-8").rstrip() for f in references]
    if assets:
        parts.append(ASSETS_INTRO.rstrip())
        parts += [f.read_text(encoding="utf-8").rstrip() for f in assets]

    return "\n\n\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只檢查 STANDALONE.md 是否為最新，不寫檔")
    args = ap.parse_args()

    stale = []
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists()):
        content = build(skill_dir)
        out = skill_dir / "STANDALONE.md"

        if args.check:
            current = out.read_text(encoding="utf-8") if out.exists() else ""
            if current == content:
                print(f"{skill_dir.name}/STANDALONE.md 為最新。")
            else:
                stale.append(skill_dir.name)
            continue

        out.write_text(content, encoding="utf-8")
        n_ref = len(references_of(skill_dir))
        n_asset = len(list((skill_dir / "assets").glob("*.md")))
        print(f"已產生：{skill_dir.name}/STANDALONE.md"
              f"（SKILL.md ＋ references {n_ref} 份 ＋ assets {n_asset} 份，"
              f"共 {content.count(chr(10)) + 1} 行 / {len(content):,} 字元）")

    if stale:
        sys.exit(f"與分檔不一致：{'、'.join(stale)}；請執行 python tools/build_standalone.py")


def references_of(skill_dir: Path):
    return sorted((skill_dir / "references").glob("*.md"))


if __name__ == "__main__":
    main()
