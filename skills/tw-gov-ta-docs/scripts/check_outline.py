#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 Word 檔的自動標號算出來印成大綱，用來驗證「壹 > 一 > (一) > 1 > (1)」編對了。

    python tools/check_docx_outline.py <檔案.docx> [--全部]

Word 的標號存在 numbering.xml 裡、開檔時才算出來，檔案的段落文字**不含標號**，
所以肉眼看 XML 或用 python-docx 讀 `paragraph.text` 都看不出編號對不對。本腳本照
Word 的規則重算一次：掛到某層就把該層加一、下面各層歸零，再套 lvlText 印出來。

預設只印有標號的段落；`--全部` 連內文一起印，用來檢查段落有沒有掛錯樣式。
"""
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

DIGITS = {
    "decimal": lambda n: str(n),
    "taiwaneseCountingThousand": lambda n: _cn(n, "一二三四五六七八九"),
    "ideographLegalTraditional": lambda n: _cn(n, "壹貳參肆伍陸柒捌玖"),
    "chineseCounting": lambda n: _cn(n, "一二三四五六七八九"),
}
TENS = {"taiwaneseCountingThousand": "十", "chineseCounting": "十", "ideographLegalTraditional": "拾"}


def _cn(n, digits, ten="十"):
    if n < 10:
        return digits[n - 1]
    if n < 20:
        return ten + (digits[n % 10 - 1] if n % 10 else "")
    return digits[n // 10 - 1] + ten + (digits[n % 10 - 1] if n % 10 else "")


def load(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    return {name: etree.fromstring(parts[name]) for name in
            ("word/document.xml", "word/styles.xml", "word/numbering.xml") if name in parts}


def numbering_map(styles, numbering):
    """styleId → (ilvl, numFmt, lvlText)，只收真的會印出標號的層級。"""
    num_to_abs = {n.get(W + "numId"): n.find(W + "abstractNumId").get(W + "val")
                  for n in numbering.findall(W + "num")}
    levels = {}
    for a in numbering.findall(W + "abstractNum"):
        for lvl in a.findall(W + "lvl"):
            fmt = lvl.find(W + "numFmt")
            text = lvl.find(W + "lvlText")
            levels[(a.get(W + "abstractNumId"), lvl.get(W + "ilvl"))] = (
                fmt.get(W + "val") if fmt is not None else "none",
                text.get(W + "val") if text is not None else "")

    out = {}
    for s in styles.findall(W + "style"):
        numPr = s.find(W + "pPr/" + W + "numPr")
        if numPr is None:
            continue
        numId = numPr.find(W + "numId")
        ilvl = numPr.find(W + "ilvl")
        numId = numId.get(W + "val") if numId is not None else None
        ilvl = ilvl.get(W + "val") if ilvl is not None else "0"
        key = (num_to_abs.get(numId), ilvl)
        if key in levels and levels[key][0] != "none":
            out[s.get(W + "styleId")] = (int(ilvl), *levels[key])
    return out


def render_label(fmt, lvl_text, counters):
    label = lvl_text
    for i, n in enumerate(counters, start=1):
        token = f"%{i}"
        if token in label:
            label = label.replace(token, DIGITS.get(fmt, str)(n) if n else token)
    return label


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_all = "--全部" in sys.argv
    if not argv:
        sys.exit("用法：python tools/check_docx_outline.py <檔案.docx> [--全部]")
    path = Path(argv[0])
    parts = load(path)
    styles = numbering_map(parts["word/styles.xml"], parts["word/numbering.xml"])

    counters = [0] * 9
    seen = 0
    used = {}
    for p in parts["word/document.xml"].iter(W + "p"):
        pStyle = p.find(W + "pPr/" + W + "pStyle")
        style_id = pStyle.get(W + "val") if pStyle is not None else None
        text = "".join(t.text or "" for t in p.iter(W + "t")).strip()

        if style_id in styles:
            ilvl, fmt, lvl_text = styles[style_id]
            counters[ilvl] += 1
            for i in range(ilvl + 1, len(counters)):
                counters[i] = 0
            label = render_label(fmt, lvl_text, counters[:ilvl + 1])
            print(f"{'    ' * ilvl}{label} {text}")
            seen += 1
            used[style_id] = used.get(style_id, 0) + 1
        elif show_all and text:
            print(f"{'    ' * 5}· [{style_id}] {text[:60]}")

    # 只有「本文用到的樣式」才代表這份文件的標號層數。styles.xml 通常含多組
    # numbering 定義（範本從真實案件萃取時一併帶進的殘留），把它們的 ilvl 混在
    # 一起數，會把五層看成六層——所以未使用者另行分組列出。
    order = lambda kv: (kv[1][0], kv[0])
    hit = sorted(((s, v) for s, v in styles.items() if s in used), key=order)
    miss = sorted(((s, v) for s, v in styles.items() if s not in used), key=order)

    print(f"\n共 {seen} 個自動標號段落，實際用到 {len({v[0] for s, v in hit})} 層。")
    print("本文使用：" + "、".join(f"{s}→ilvl{v[0]}（{used[s]} 段）" for s, v in hit))
    if miss:
        print("未使用（styles.xml 有定義，本文未套用，不計入層數）："
              + "、".join(f"{s}→ilvl{v[0]}" for s, v in miss))


if __name__ == "__main__":
    main()
