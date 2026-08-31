#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從結案案例 Word 檔萃取版面規格，產生 skills/tw-gov-ta-docs/assets/工作說明書範本.docx。

    python tools/make_template.py <結案案例.docx>

範本＝來源檔的**樣式、編號、頁面設定、頁首頁尾**，內容全部清空。字體、字級、縮排、
行距、邊界都留在範本的 styles.xml／sectPr 裡，`make_docx.py` 只掛樣式、不再寫死任何
版面數值——版面規格只有範本這一份，改版面請改範本，不要改腳本。

來源檔是真實案件，範本必須可公開，因此本腳本一併清除：機關與案名（頁首改為 ○○○
佔位）、docProps 的作者、修訂紀錄與時間戳、app.xml 的頁數字數等統計、settings.xml 的
rsid 編修痕跡，以及全部本文段落。清完後範本裡只剩版面：styles.xml、numbering.xml、
sectPr、頁首頁尾框線與字體。

## 編號：改掉來源檔的手動重編作法

來源檔的五層標號（壹／一／(一)／1／(1)）各自是一個獨立的單層編號定義，沒有層級關係；
每遇到新一節要讓標號從 1 重來，作者就另外建一個 numId 加 startOverride，全篇共 32 個。
在 Word 裡插入或搬動章節時這些重編點不會跟著走，標號就錯了。

本腳本改寫成 Word 原生的單一多層清單（一個 abstractNum，五個 ilvl，各層綁定對應樣式），
上層跳號時下層自動歸 1，插入章節後全篇自動重編。**外觀與來源檔一致**（標號格式、縮排、
懸掛值都照來源檔實測值），換掉的只是它底下的實作方式。
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "skills" / "tw-gov-ta-docs" / "assets" / "工作說明書範本.docx"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

HEADER_PLACEHOLDER = "○○○　○○○"      # 機關全銜　案名，make_docx.py 於產生草稿時代換

# 五層標號 → 來源檔樣式 styleId。lvlText／ind 為來源檔實測值，換算後與樣式本身的縮排一致。
LEVELS = [
    # (styleId, numFmt, lvlText, ind 屬性)
    ("10", "ideographLegalTraditional", "%1、", {"left": "0", "firstLine": "0"}),
    ("2",  "taiwaneseCountingThousand", "%2、", {"left": "766",  "hanging": "482"}),
    ("3",  "taiwaneseCountingThousand", "(%3)", {"left": "1049", "hanging": "482"}),
    ("4",  "decimal",                   "%4.",  {"left": "1758", "hanging": "482"}),
    ("5",  "decimal",                   "(%5)", {"left": "2183", "hanging": "482"}),
]
NEW_ABSTRACT_ID = "100"
NEW_NUM_ID = "100"

# 來源檔的封面與表格是逐段手動設定格式、沒有樣式可掛，這裡補成具名樣式，讓
# make_docx.py 掛樣式就好，版面數值一樣只存在範本裡。封面數值取自來源檔封面段落實測值
# （標楷體 16pt、行高 24pt 固定、置中、字元間距 -1pt）。
EXTRA_STYLES = """
<w:style xmlns:w="{ns}" w:type="paragraph" w:customStyle="1" w:styleId="cover">
  <w:name w:val="封面"/><w:basedOn w:val="a1"/><w:qFormat/>
  <w:pPr><w:adjustRightInd w:val="0"/><w:snapToGrid w:val="0"/>
    <w:spacing w:line="480" w:lineRule="exact"/><w:jc w:val="center"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="標楷體" w:eastAsia="標楷體" w:hAnsi="標楷體"/>
    <w:spacing w:val="-20"/><w:sz w:val="32"/><w:szCs w:val="44"/></w:rPr>
</w:style>
<w:style xmlns:w="{ns}" w:type="paragraph" w:customStyle="1" w:styleId="coverNote">
  <w:name w:val="封面註記"/><w:basedOn w:val="cover"/><w:qFormat/>
  <w:rPr><w:spacing w:val="0"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
</w:style>
<w:style xmlns:w="{ns}" w:type="paragraph" w:customStyle="1" w:styleId="tableText">
  <w:name w:val="表格內文"/><w:basedOn w:val="a1"/><w:qFormat/>
  <w:pPr><w:snapToGrid w:val="0"/><w:spacing w:line="320" w:lineRule="exact"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="標楷體" w:eastAsia="標楷體" w:hAnsi="標楷體"/><w:sz w:val="24"/></w:rPr>
</w:style>
"""


def parse(data):
    return etree.fromstring(data)


def serialize(tree):
    return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)


def strip_body(document_xml):
    """清空本文，只留 sectPr（頁面設定與頁首頁尾參照）。"""
    root = parse(document_xml)
    body = root.find(W + "body")
    sectPr = body.find(W + "sectPr")
    for child in list(body):
        if child is not sectPr:
            body.remove(child)
    return serialize(root)


def blank_header(header_xml):
    """頁首只留一段一個 run，文字換成佔位符；字體與框線設定原樣保留。"""
    root = parse(header_xml)
    paragraphs = root.findall(W + "p")
    keep = paragraphs[0]
    for p in paragraphs[1:]:
        root.remove(p)
    runs = keep.findall(W + "r")
    for r in runs[1:]:
        keep.remove(r)
    if runs:
        first = runs[0]
        for t in first.findall(W + "t"):
            first.remove(t)
        t = etree.SubElement(first, W + "t")
        t.text = HEADER_PLACEHOLDER
    return serialize(root)


def scrub_core_props(core_xml):
    """移除作者、修訂者、列印與修訂時間這類來源檔的個人與案件痕跡。"""
    text = core_xml.decode("utf-8")
    for tag in ("dc:title", "dc:subject", "dc:creator", "cp:keywords",
                "dc:description", "cp:lastModifiedBy"):
        text = re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}></{tag}>", text, flags=re.S)
        text = re.sub(rf"<{tag}/>", f"<{tag}></{tag}>", text)
    text = re.sub(r"<cp:revision>.*?</cp:revision>", "<cp:revision>1</cp:revision>", text, flags=re.S)
    # 時間戳整個拿掉而不是換成假日期：範本沒有「建立於某日」這件事，留空欄位比留一個
    # 編出來的日期誠實。lastPrinted 同理。
    for tag in ("cp:lastPrinted", "dcterms:created", "dcterms:modified"):
        text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", text, flags=re.S)
    return text.encode("utf-8")


def scrub_app_props(app_xml):
    """歸零 docProps/app.xml 的統計欄位。

    本文已經清空，這些數字卻是來源檔的——12 頁、1128 字、編修 142 分鐘。洩不出實質
    內容，但它們描述的是一份不存在於本範本的文件，留著只會讓人以為範本裡還有東西。
    """
    text = app_xml.decode("utf-8")
    for tag in ("TotalTime", "Pages", "Words", "Characters", "Lines",
                "Paragraphs", "CharactersWithSpaces"):
        text = re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}>0</{tag}>", text, flags=re.S)
    return text.encode("utf-8")


def strip_rsids(settings_xml):
    """rsid 是逐次編修留下的識別碼，範本用不到，清掉可少 100KB 以上。"""
    root = parse(settings_xml)
    for tag in ("rsids",):
        el = root.find(W + tag)
        if el is not None:
            root.remove(el)
    return serialize(root)


def build_multilevel(nsid="4A3B2C10"):
    """單一多層清單：五個 ilvl 各綁一個樣式，上層跳號時下層自動歸 1。"""
    a = etree.Element(W + "abstractNum", nsmap={"w": NS_W})
    a.set(W + "abstractNumId", NEW_ABSTRACT_ID)
    etree.SubElement(a, W + "nsid").set(W + "val", nsid)
    etree.SubElement(a, W + "multiLevelType").set(W + "val", "multilevel")
    etree.SubElement(a, W + "tmpl").set(W + "val", nsid)
    for ilvl, (style_id, fmt, text, ind) in enumerate(LEVELS):
        lvl = etree.SubElement(a, W + "lvl")
        lvl.set(W + "ilvl", str(ilvl))
        etree.SubElement(lvl, W + "start").set(W + "val", "1")
        etree.SubElement(lvl, W + "numFmt").set(W + "val", fmt)
        etree.SubElement(lvl, W + "pStyle").set(W + "val", style_id)
        etree.SubElement(lvl, W + "lvlText").set(W + "val", text)
        etree.SubElement(lvl, W + "lvlJc").set(W + "val", "left")
        pPr = etree.SubElement(lvl, W + "pPr")
        ind_el = etree.SubElement(pPr, W + "ind")
        for k, v in ind.items():
            ind_el.set(W + k, v)

    n = etree.Element(W + "num", nsmap={"w": NS_W})
    n.set(W + "numId", NEW_NUM_ID)
    etree.SubElement(n, W + "abstractNumId").set(W + "val", NEW_ABSTRACT_ID)
    return a, n


def repoint_styles(styles_xml):
    """五個標號樣式改指向新的多層清單；回傳（新 styles.xml, 仍被樣式引用的 numId 集合）。"""
    root = parse(styles_xml)
    wanted = {sid: ilvl for ilvl, (sid, *_rest) in enumerate(LEVELS)}
    for s in root.findall(W + "style"):
        sid = s.get(W + "styleId")
        pPr = s.find(W + "pPr")
        if sid in wanted:
            if pPr is None:
                pPr = etree.SubElement(s, W + "pPr")
            numPr = pPr.find(W + "numPr")
            if numPr is None:
                numPr = etree.Element(W + "numPr")
                pPr.insert(0, numPr)
            for child in list(numPr):
                numPr.remove(child)
            etree.SubElement(numPr, W + "ilvl").set(W + "val", str(wanted[sid]))
            etree.SubElement(numPr, W + "numId").set(W + "val", NEW_NUM_ID)

    for chunk in etree.fromstring(
            f'<w:wrap xmlns:w="{NS_W}">{EXTRA_STYLES.format(ns=NS_W)}</w:wrap>'):
        root.append(chunk)

    referenced = {NEW_NUM_ID}
    for numId in root.iter(W + "numId"):
        val = numId.get(W + "val")
        if val:
            referenced.add(val)
    return serialize(root), referenced


def prune_numbering(numbering_xml, referenced_num_ids):
    """本文清空後，那 32 個手動重編的 numId 已無人引用，連同孤兒 abstractNum 一起刪除。"""
    root = parse(numbering_xml)
    new_abs, new_num = build_multilevel()

    kept_nums = []
    for n in root.findall(W + "num"):
        if n.get(W + "numId") in referenced_num_ids:
            kept_nums.append(n)
        else:
            root.remove(n)

    live_abstract = {n.find(W + "abstractNumId").get(W + "val") for n in kept_nums}
    live_abstract.add(NEW_ABSTRACT_ID)
    for a in root.findall(W + "abstractNum"):
        if a.get(W + "abstractNumId") not in live_abstract:
            root.remove(a)

    first_num = root.find(W + "num")
    if first_num is not None:
        first_num.addprevious(new_abs)
    else:
        root.append(new_abs)
    root.append(new_num)
    return serialize(root)


TRANSFORMS = {
    "word/document.xml": strip_body,
    "word/header1.xml": blank_header,
    "docProps/core.xml": scrub_core_props,
    "docProps/app.xml": scrub_app_props,
    "word/settings.xml": strip_rsids,
}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"找不到來源檔：{src}")

    with zipfile.ZipFile(src) as zin:
        parts = {name: zin.read(name) for name in zin.namelist()}

    styles_xml, referenced = repoint_styles(parts["word/styles.xml"])
    parts["word/styles.xml"] = styles_xml
    parts["word/numbering.xml"] = prune_numbering(parts["word/numbering.xml"], referenced)
    for name, fn in TRANSFORMS.items():
        if name in parts:
            parts[name] = fn(parts[name])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".docx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in parts.items():
            zout.writestr(name, data)
    shutil.move(str(tmp), str(OUT))

    print(f"已產生：{OUT.relative_to(ROOT)}（{OUT.stat().st_size:,} bytes，"
          f"來源 {src.stat().st_size:,} bytes）")
    for sid, fmt, text, _ind in LEVELS:
        print(f"  樣式 {sid:>3} → {text}（{fmt}）")


if __name__ == "__main__":
    main()
