#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
將 assets/工作說明書骨架.md 轉成 Word 檔，供顧問協辦情境使用。

    python scripts/make_docx.py [骨架.md路徑] [輸出資料夾]

版面規格（邊界、頁首頁尾距離、標題／內文字體）取自 `工作說明書_V3.1.docx`
的實測值，不是重新沿用 `tw-gov-it-docs` 那份 `make_docx_skeleton.py` 的參數——
兩者各自獨立維護，改一邊不影響另一邊。

輸出檔名固定為 `工作說明書_V0.0.docx`，不含日期或案名，避免每次重新產生
還要對應改檔名；要保留舊版就在覆寫前自行備份。

骨架裡要插入表格或圖片時，在表格前一行單獨寫 `[表] 標題文字`（圖片用 `[圖]`），本腳本會依
當時所屬章節即時算出「章-序」編號（例如「表 2-1」）並直接寫成文字，**不是** Word 的
SEQ／STYLEREF 欄位。骨架標題是打字輸入的中文數字（壹、貳、參…），Word 沒有原生機制能對這種
標題自動算章節號；若之後在 Word 裡手動調整章節順序或插入新章，既有的表號**不會**自動跟著變，
需重新執行本腳本或於 Word 內手動修正。
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Twips, Pt

# ---- V3.1 實測版面規格 ----
MARGIN = Twips(1134)          # 上下左右邊界，實測值（工作說明書_V3.1.docx sectPr pgMar）
HEADER_DIST = Twips(992)      # 頁首距頁緣
FOOTER_DIST = Twips(737)      # 頁尾距頁緣

HEAD_FONT = "標楷體"           # 標題字體（章／節／目／款）
BODY_FONT = "新細明體"         # 內文字體
ASCII_FONT = "Times New Roman"

# 標題層級對應的字級、是否粗體；HEADING_RE 抓到幾個 # 就對應這裡第幾層
HEAD_STYLE = {
    2: (16, True),   # ## 壹、貳、參…（章）
    3: (14, True),   # ### 一、二、三…（節）
    4: (13, True),   # #### （一）（二）（三）…（目）
}
BODY_SIZE = 12

# 縮排：政府文書處理手冊對分項條列縮排唯一明文的規定是「下一層應另列縮一格書寫」
# （國家發展委員會《政府文書格式參考規範》）——沒有逐層字元數的官方對照表，網路流傳的
# 那種「大項4字元/3字元、第一層7字元/3字元…」細表查無官方出處，其懸掛縮排算法本身也
# 兜不攏（縮排−懸掛≠標號起始位置），不予採信。
#
# 這裡改用 Word 原生的字元縮排（w:leftChars／w:hangingChars，而非把 Pt/Cm 換算值硬塞進
# left_indent 充數）落實「多縮一格」：1 字元＝內文字級（12pt）寬度，每深一層 leftChars+1；
# 條列項目另加 hangingChars=1，讓標號貼齊上一層的內容起始位置，換行內容才對得齊標號，
# 不是每行都跟標號同一個縮排。細節見 set_char_indent()。
CHAR_UNIT_PT = BODY_SIZE

OUTPUT_NAME = "工作說明書_V0.0.docx"

HEADING_RE = re.compile(r"^(#{2,4})\s+(.*)")
PAREN_RE = re.compile(r"^（([一二三四五六七八九十]+)）\s*(.*)")
ORDERED_RE = re.compile(r"^(\d+)\.\s+(.*)")
ORDERED_PAREN_RE = re.compile(r"^\((\d+)\)\s*(.*)")   # (1)(2)… 第四層，依官方規定用半形括號
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
CAPTION_RE = re.compile(r"^\[(表|圖)\]\s*(.*)")


def set_font(run, name=BODY_FONT, size=BODY_SIZE, bold=False):
    run.font.name = ASCII_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), ASCII_FONT)
    rfonts.set(qn("w:hAnsi"), ASCII_FONT)


def set_char_indent(paragraph, left_chars=None, hanging_chars=None, first_line_chars=None):
    """套用 Word 原生的字元縮排（w:leftChars／w:hangingChars／w:firstLineChars），對應
    Word 段落對話框「進階版面配置」勾選字元單位時寫出的屬性，不是拿絕對長度湊視覺效果。
    同時换算寫入對應的絕對長度（w:left／w:hanging／w:firstLine）當備援，給不支援字元
    單位的檢視器/轉檔器用；Word 開啟時仍以字元屬性為準。"""
    ind = paragraph._p.get_or_add_pPr().get_or_add_ind()
    if left_chars is not None:
        ind.left = Pt(left_chars * CHAR_UNIT_PT)
        ind.set(qn("w:leftChars"), str(left_chars * 100))
    if hanging_chars is not None:
        ind.hanging = Pt(hanging_chars * CHAR_UNIT_PT)
        ind.set(qn("w:hangingChars"), str(hanging_chars * 100))
    if first_line_chars is not None:
        ind.firstLine = Pt(first_line_chars * CHAR_UNIT_PT)
        ind.set(qn("w:firstLineChars"), str(first_line_chars * 100))


def add_runs_with_inline_bold(p, text, font=BODY_FONT, size=BODY_SIZE, base_bold=False):
    """支援行內 **粗體**；非粗體片段沿用 base_bold（標題整段粗體時仍保持粗體）。"""
    pos = 0
    for m in BOLD_RE.finditer(text):
        if m.start() > pos:
            set_font(p.add_run(text[pos:m.start()]), font, size, base_bold)
        set_font(p.add_run(m.group(1)), font, size, True)
        pos = m.end()
    if pos < len(text):
        set_font(p.add_run(text[pos:]), font, size, base_bold)


def bottom_border(paragraph):
    pPr = paragraph._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "auto")
    pBdr.append(bottom)
    pPr.append(pBdr)


def build_header_footer(section, agency_placeholder="○○○", case_placeholder="○○○"):
    """頁首左靠（比照 V3.1 header1.xml，未見 jc 置中覆寫），只放機關與案名，不夾帶草稿註記。"""
    header = section.header
    hp = header.paragraphs[0]
    set_font(hp.add_run(f"{agency_placeholder}　{case_placeholder}"), HEAD_FONT, 10)
    bottom_border(hp)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    set_font(run, ASCII_FONT, 10)
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._element.append(fld_begin)
    run._element.append(instr)
    run._element.append(fld_sep)
    run._element.append(fld_end)


def suppress_header_footer_on_cover(section):
    """封面不出現跑馬頁首頁尾（V3.1 的頁首是工作內容頁才需要的識別列，封面本身已有案名大字）。"""
    sectPr = section._sectPr
    titlePg = OxmlElement("w:titlePg")
    sectPr.append(titlePg)
    section.different_first_page_header_footer = True
    # 首頁頁首頁尾留空即可，first_page_header/footer 預設為空白段落


def build_cover(doc, meta):
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(meta["機關"]), HEAD_FONT, 22, True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(meta["案名"]), HEAD_FONT, 20, True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("工作說明書"), HEAD_FONT, 26, True)

    for _ in range(6):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(f"版本：{meta['版本']}"), BODY_FONT, 12)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(f"日期：{meta['日期']}"), BODY_FONT, 12)

    doc.add_page_break()


def build_version_table(doc):
    p = doc.add_paragraph()
    set_font(p.add_run("文件版本紀錄"), HEAD_FONT, 14, True)
    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, h in enumerate(["版本", "日期", "修訂內容", "修訂人"]):
        set_font(table.rows[0].cells[i].paragraphs[0].add_run(h), BODY_FONT, 11, True)
    row = table.add_row()
    for i, v in enumerate(["V0.0", "○○○", "顧問初稿", "○○○"]):
        set_font(row.cells[i].paragraphs[0].add_run(v), BODY_FONT, 11)
    doc.add_page_break()


class Renderer:
    def __init__(self, doc):
        self.doc = doc
        self.chapter_no = 0     # 目前所在「壹、貳、參…」章序號（阿拉伯數字）
        self.caption_seq = {}   # {(kind, chapter_no): 已用序號}
        self.in_paren = False   # 目前是否在（一）（二）…區塊內，決定底下 1. 2. 3. 要縮幾階
        self.last_list_chars = 1  # 上一個 1.2.3 項目的 leftChars，(1)(2)… 接在它底下時再深一格

    def add_caption(self, kind, text):
        self.caption_seq[(kind, self.chapter_no)] = self.caption_seq.get((kind, self.chapter_no), 0) + 1
        n = self.caption_seq[(kind, self.chapter_no)]
        p = self.doc.add_paragraph()
        set_font(p.add_run(f"{kind} {self.chapter_no}-{n}　"), BODY_FONT, 11, True)
        set_font(p.add_run(text), BODY_FONT, 11)
        return p

    def render(self, md_text):
        lines = md_text.split("\n")
        i = 0
        table_buf = []
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if TABLE_ROW_RE.match(stripped):
                table_buf.append(stripped)
                i += 1
                continue
            if table_buf:
                self._flush_table(table_buf)
                table_buf = []

            if not stripped:
                i += 1
                continue

            m = HEADING_RE.match(stripped)
            if m:
                level = len(m.group(1))
                text = m.group(2).strip()
                if level == 2:
                    self.chapter_no += 1
                self.in_paren = False
                self.last_list_chars = 1
                self._add_heading(level, text)
                i += 1
                continue

            m = CAPTION_RE.match(stripped)
            if m:
                self.add_caption(m.group(1), m.group(2))
                i += 1
                continue

            m = PAREN_RE.match(stripped)
            if m:
                self.in_paren = True
                size, bold = HEAD_STYLE[4]
                p = self.doc.add_paragraph()
                set_char_indent(p, left_chars=1)
                add_runs_with_inline_bold(p, f"（{m.group(1)}）{m.group(2)}", HEAD_FONT, size, bold)
                i += 1
                continue

            m = BLOCKQUOTE_RE.match(stripped)
            if m:
                # > 區塊是骨架給撰寫者看的挖空／寫法指引，不是文件內容——
                # 依規定填空提示不進入交付的 Word 檔，整段吃掉不輸出。
                i += 1
                while i < len(lines) and BLOCKQUOTE_RE.match(lines[i].strip()):
                    i += 1
                continue

            m = ORDERED_RE.match(stripped)
            if m:
                left_chars = 2 if self.in_paren else 1
                self.last_list_chars = left_chars
                p = self.doc.add_paragraph()
                set_char_indent(p, left_chars=left_chars, hanging_chars=1)
                add_runs_with_inline_bold(p, f"{m.group(1)}.　{m.group(2)}", BODY_FONT, BODY_SIZE)
                i += 1
                continue

            m = ORDERED_PAREN_RE.match(stripped)
            if m:
                left_chars = self.last_list_chars + 1
                p = self.doc.add_paragraph()
                set_char_indent(p, left_chars=left_chars, hanging_chars=1)
                add_runs_with_inline_bold(p, f"({m.group(1)})　{m.group(2)}", BODY_FONT, BODY_SIZE)
                i += 1
                continue

            # 一般內文段落：首行縮排 2 字元；在（一）（二）…區塊內時，段落本身也跟著那一階的左縮排走
            p = self.doc.add_paragraph()
            set_char_indent(p, left_chars=(1 if self.in_paren else None), first_line_chars=2)
            add_runs_with_inline_bold(p, stripped, BODY_FONT, BODY_SIZE)
            i += 1

        if table_buf:
            self._flush_table(table_buf)

    def _add_heading(self, level, text):
        size, bold = HEAD_STYLE[level]
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(4)
        add_runs_with_inline_bold(p, text, HEAD_FONT, size, bold)

    def _flush_table(self, rows_raw):
        rows = [[c.strip() for c in r.strip("|").split("|")] for r in rows_raw]
        if len(rows) >= 2 and set(rows[1][0]) <= set("-: "):
            del rows[1]
        table = self.doc.add_table(rows=0, cols=len(rows[0]))
        table.style = "Table Grid"
        for r_i, row in enumerate(rows):
            cells = table.add_row().cells
            for c_i, val in enumerate(row):
                if c_i >= len(cells):
                    continue
                run = cells[c_i].paragraphs[0].add_run(val)
                set_font(run, BODY_FONT, 11, r_i == 0)


def main():
    md_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "assets" / "工作說明書骨架.md"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()

    text = md_path.read_text(encoding="utf-8")
    # 第一個表格（封面欄位表）與其餘骨架分開處理
    body_start = text.index("## 壹、")
    meta_block = text[:body_start]
    body_text = text[body_start:]

    meta = {"機關": "○○○", "案名": "○○○", "版本": "顧問草稿 V0.0", "日期": "○○○"}
    for row in re.findall(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", meta_block):
        key, val = row
        if key in meta and "---" not in val:
            meta[key] = val

    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = MARGIN
    section.left_margin = section.right_margin = MARGIN
    section.header_distance = HEADER_DIST
    section.footer_distance = FOOTER_DIST

    build_header_footer(section, meta["機關"], meta["案名"])
    suppress_header_footer_on_cover(section)

    build_cover(doc, meta)
    build_version_table(doc)

    Renderer(doc).render(body_text)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / OUTPUT_NAME
    doc.save(out_path)
    print(f"已產生：{out_path}")


if __name__ == "__main__":
    main()
