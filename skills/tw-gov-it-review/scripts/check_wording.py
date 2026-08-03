#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公部門技術文件用語檢查：掃描草稿中會被退件的機械性錯誤。

用法：
    python scripts/check_wording.py 草稿.md
    python scripts/check_wording.py 需求規格書.md 設計規格書.md
    python scripts/check_wording.py references              # 可傳目錄
    python scripts/check_wording.py 草稿.md --只看錯誤
    python scripts/check_wording.py 草稿.md --無待填清單
    python scripts/check_wording.py --rules                  # 列出目前載入的規則

檢查項目：
    [錯誤] 簡體字                     ← 內建對照表
    [錯誤] 中國大陸用語與非標準用字   ← 規則來自 references/02-用語與表達.md
    [錯誤] 法律統一用字（部份→部分等） ← 同上，依立法院「法律統一用字表」
    [錯誤] 已停止適用的法規名稱       ← 規則來自 references/03-法規速查.md
    [建議] 用語偏好（網路安全→資通安全等）← 規則來自 references/02-用語與表達.md
    [建議] 不可驗收的字眼             ← 同上
    [建議] 行銷語言                   ← 同上
    [建議] 標點：中文句中的半形標點、包住中文的半形括號、標題結尾帶標點
    [建議] 全半形：全形英文字母與數字
    [建議] 數字用法：序數用中文數字（依「公文書橫式書寫數字使用原則」）
    [清單] 全部【待填】的位置

前七項的詞表在 references/ 內；標點、全半形、數字三項屬規則式判斷，寫在本檔。
程式碼區塊（``` 圍起來的段落）、行內程式碼與網址不做檢查。

注意：從 PDF 貼出來的草稿，全形括號常在抽取時被轉成半形，會產生大量
      「改用全形括號」的[建議]。那是抽取失真，不是原文的問題。

規則不寫在本檔內，一律讀 references/ 的表格，避免兩邊不一致。
要新增規則請改 `references/02-用語與表達.md` 中標記【檢查規則】的表格。

若某一行是刻意要提到禁用詞（例如檢核清單本身），在行尾加上
`<!-- 檢查略過 -->` 即可跳過該行。

離開碼：有[錯誤]時為 1，其餘為 0，可用於 CI。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE_REF = ROOT / "references" / "02-用語與表達.md"
COMPLIANCE_REF = ROOT / "references" / "03-法規速查.md"

IGNORE_MARK = "<!-- 檢查略過 -->"

# 常見於資訊系統文件的「正體－簡化」對照。以空白分隔，每組兩字。
# 兩字相同者（無簡化差異）與下方 AMBIGUOUS 名單會自動排除，
# 避免把「布」「准」「余」這類正體字也判成簡體。
_PAIRS = (
    "軟软 網网 絡络 資资 訊讯 據据 庫库 應应 該该 項项 計计 劃划 設设 備备 詢询 認认 證证 "
    "權权 報报 單单 圖图 檔档 會会 議议 員员 時时 間间 發发 測测 試试 "
    "環环 結结 變变 風风 險险 責责 機机 關关 電电 腦脑 統统 "
    "業业 務务 開开 產产 質质 標标 導导 覽览 選选 執执 驗验 節节 點点 "
    "維维 護护 儲储 傳传 輸输 載载 錄录 齡龄 續续 擬拟 個个 們们 為为 與与 對对 "
    "從从 麼么 樣样 這这 種种 廠厂 買买 賣卖 貨货 費费 稱称 職职 級级 類类 態态 "
    "擊击 龍龙 齊齐 縣县 鄉乡 區区 學学 師师 訓训 練练 課课 "
    "義义 觀观 覺觉 藝艺 蘭兰 灣湾 廣广 東东 屬属 屆届 舊旧 陽阳 陰阴 "
    "適适 舉举 擁拥 擴扩 檢检 綜综 線线 纖纤 "
    "組组 織织 給给 絕绝 經经 總总 縮缩 績绩 繳缴 繼继 "
    "轉转 較较 輔辅 軌轨 輪轮 農农 運运 遠远 遞递 邊边 鄰邻 醫医 釋释 "
    "鍵键 鎖锁 鐘钟 鑑鉴 長长 門门 閉闭 陣阵 隊队 階阶 隨随 "
    "難难 靈灵 頁页 順顺 預预 領领 頭头 顯显 飛飞 館馆 馬马 "
    "駕驾 體体 齒齿 憑凭 檢检 覆复 幣币 舉举 讓让 認认 屬属"
)
# 正體中文本來就有、不可判為簡體的字（多為一字兩用或另有本義）
AMBIGUOUS = set("布准余台才行理面里只于後干發表系存收任限更程雲云")

SIMPLIFIED = {
    pair[1] for pair in _PAIRS.split()
    if len(pair) == 2 and pair[0] != pair[1] and pair[1] not in AMBIGUOUS
}


def parse_rule_tables(path: Path):
    """讀取標記【檢查規則】的表格。回傳 [(分類, 避免用, 建議改為, 說明)]。"""
    rules = []
    if not path.exists():
        return rules
    section = None
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            active = "【檢查規則】" in section
            section = section.replace("【檢查規則】", "").strip()
            continue
        if not active or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("避免用",) or set(cells[0]) <= set("-: "):
            continue
        bad_list = [b.strip() for b in cells[0].split("、") if b.strip()]
        good_list = [g.strip() for g in cells[1].split("、") if g.strip()]
        note = cells[2] if len(cells) > 2 else ""
        if len(good_list) == len(bad_list):
            pairs = zip(bad_list, good_list)
        else:
            pairs = ((b, cells[1]) for b in bad_list)
        for bad, good in pairs:
            rules.append((section, bad, good, note))
    return rules


def parse_obsolete_laws(path: Path):
    """讀取「已停止適用，不得再引用」表格的舊名稱。"""
    names = []
    if not path.exists():
        return names
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            active = "已停止適用" in line
            continue
        if not active or not line.startswith("|"):
            continue
        cell = line.strip().strip("|").split("|")[0].strip()
        if cell in ("舊名稱",) or set(cell) <= set("-: "):
            continue
        cell = cell.replace("**", "")
        found = re.findall(r"「([^」]+)」", cell)
        names.extend(f for f in found if len(f) >= 4)
    return names


SEVERITY = {
    "常見用字": "錯誤",
    "法律統一用字": "錯誤",
    "用語偏好": "建議",
    "不可驗收的字眼": "建議",
    "不要用的行銷語言": "建議",
}

# 某個詞出現在更長的正確詞組裡時不算違規，避免切詞誤判。
# 無法用「詞對詞」列舉的（如「質量」＝質與量、「內存」←「範圍內存取」），
# 一律不列入自動規則，改列 02-用語與表達.md 的人工判斷表。
EXCEPTIONS = {
    "用戶": ("用戶端",),
    "應可": ("對應可", "相應可", "反應可"),   # 「對應可檢視的成果」不是承諾留退路
}

PLACEHOLDER_RE = re.compile(r"【待填[^】]*】")

# ---- 規則式（機械判斷）檢查 ----------------------------------------------
# 這幾項無法用「詞對詞」的表格表達，故寫在程式內；判斷依據見
# references/02-用語與表達.md 的「數字用法」與「標點符號與全形半形」兩節。

CJK = r"一-鿿"

# 半形標點夾在中文之間（前後都是中文才算，避免誤判英文、路徑、程式碼）
HALFWIDTH_PUNCT_RE = re.compile(rf"[{CJK}][,;?!][{CJK}]")
# 半形括號包住中文
HALFWIDTH_PAREN_RE = re.compile(rf"\([^()]*[{CJK}][^()]*\)")
# 全形英文字母與數字
FULLWIDTH_ALNUM_RE = re.compile(r"[Ａ-Ｚａ-ｚ０-９]")
# 標題結尾帶標點
HEADING_PUNCT_RE = re.compile(r"^#{1,6}\s+.*[。，、；：！？,;:!?]\s*$")
# 序數宜用阿拉伯數字：限縮在明確可數的後綴，避免誤判「第一步」「第一線」
ORDINAL_SUFFIX = "階段|次會議|季|屆|優先|會議室|組|名|次"
ORDINAL_RE = re.compile(rf"第([一二三四五六七八九十]+)({ORDINAL_SUFFIX})")

# 這些檢查前先剝掉行內程式碼、網址與 markdown 連結目標，減少誤判
INLINE_CODE_RE = re.compile(r"`[^`]*`")
URL_RE = re.compile(r"https?://\S+|\]\([^)]*\)")


def strip_noise(line: str) -> str:
    return URL_RE.sub(" ", INLINE_CODE_RE.sub(" ", line))


def regex_checks(raw: str):
    """回傳 [(等級, 分類, 命中, 建議, 說明)]。"""
    out = []
    if HEADING_PUNCT_RE.match(raw):
        out.append(("建議", "標點", raw.strip()[-1], "標題結尾不加標點",
                    "立法慣用語詞：標題不使用標點符號"))
    line = strip_noise(raw)

    for m in HALFWIDTH_PUNCT_RE.finditer(line):
        out.append(("建議", "標點", m.group(0), f"改用全形標點", "中文句中混入半形標點"))
    m = HALFWIDTH_PAREN_RE.search(line)
    if m:
        out.append(("建議", "標點", m.group(0)[:20], "改用全形括號（）",
                    "括號內為中文時用全形"))
    hit_full = sorted(set(FULLWIDTH_ALNUM_RE.findall(line)))
    if hit_full:
        out.append(("建議", "全半形", "".join(hit_full), "英數字改用半形", ""))
    for m in ORDINAL_RE.finditer(line):
        out.append(("建議", "數字用法", m.group(0),
                    f"序數宜用阿拉伯數字（第 N {m.group(2)}）",
                    "公文書橫式書寫數字使用原則；描述性用語如「第一線」不在此限"))
    return out


def check_text(text: str, rules, obsolete):
    findings = []      # (行號, 等級, 分類, 命中, 建議, 說明)
    placeholders = []  # (行號, 內容)
    suppressed = []    # 被 <!-- 檢查略過 --> 跳過的行號

    in_rule_table = False
    in_code = False
    for no, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:                      # 程式碼區塊不做用語檢查
            continue
        if raw.startswith("#"):
            in_rule_table = "【檢查規則】" in raw or "已停止適用" in raw
            for level, kind, hit, good, note in regex_checks(raw):
                findings.append((no, level, kind, hit, good, note))
            continue
        if in_rule_table and raw.startswith("|"):
            continue
        # 只認「行尾」的略過標記，避免文中提到這個標記就整行被靜默跳過
        if raw.rstrip().endswith(IGNORE_MARK):
            suppressed.append(no)
            continue

        for m in PLACEHOLDER_RE.finditer(raw):
            placeholders.append((no, m.group(0)))

        # 詞表比對前先剝掉行內程式碼、網址與 markdown 連結目標，
        # 否則網址裡的 release、路徑裡的英文詞都會被當成違規。
        line = strip_noise(raw)

        hit_simplified = sorted({c for c in line if c in SIMPLIFIED})
        if hit_simplified:
            findings.append((no, "錯誤", "簡體字", "".join(hit_simplified),
                             "改為正體字", ""))

        for name in obsolete:
            if name in line:
                findings.append((no, "錯誤", "已停止適用法規", name,
                                 "見 03-法規速查.md 法規速查表", ""))

        for section, bad, good, note in rules:
            if not bad or bad not in line:
                continue
            # 命中處若全部落在例外詞組內（如「用戶」只出現在「用戶端」），不算違規
            masked = line
            for allowed in EXCEPTIONS.get(bad, ()):
                masked = masked.replace(allowed, "")
            if bad not in masked:
                continue
            findings.append((no, SEVERITY.get(section, "建議"), section,
                             bad, good, note))

        for level, kind, hit, good, note in regex_checks(raw):
            findings.append((no, level, kind, hit, good, note))

    return findings, placeholders, suppressed


def iter_files(targets):
    for t in targets:
        p = Path(t)
        if p.is_dir():
            yield from sorted(p.rglob("*.md"))
        elif p.exists():
            yield p
        else:
            print(f"找不到檔案：{p}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="要檢查的檔案或目錄（.md／.txt）")
    ap.add_argument("--只看錯誤", dest="errors_only", action="store_true")
    ap.add_argument("--無待填清單", dest="no_placeholder", action="store_true")
    ap.add_argument("--rules", action="store_true", help="列出載入的規則後結束")
    args = ap.parse_args()

    rules = parse_rule_tables(STYLE_REF)
    obsolete = parse_obsolete_laws(COMPLIANCE_REF)

    if args.rules:
        print(f"用字與語氣規則 {len(rules)} 條（來源：{STYLE_REF.name}）")
        for section, bad, good, _ in rules:
            print(f"  [{SEVERITY.get(section, '建議')}] {section}：{bad} → {good}")
        print(f"\n已停止適用法規 {len(obsolete)} 條（來源：{COMPLIANCE_REF.name}）")
        for n in obsolete:
            print(f"  {n}")
        print(f"\n簡體字表 {len(SIMPLIFIED)} 字")
        return 0

    if not args.targets:
        ap.error("請指定要檢查的檔案或目錄（--rules 可列出規則）")

    if not rules:
        print(f"警告：未從 {STYLE_REF} 讀到任何規則，請確認【檢查規則】表格是否完整。",
              file=sys.stderr)

    total_err = total_warn = total_ph = total_skip = 0
    for f in iter_files(args.targets):
        findings, placeholders, suppressed = check_text(
            f.read_text(encoding="utf-8"), rules, obsolete)
        total_skip += len(suppressed)
        if args.errors_only:
            findings = [x for x in findings if x[1] == "錯誤"]

        if findings:
            print(f"\n=== {f} ===")
            for no, level, kind, hit, good, note in findings:
                tail = f"　（{note}）" if note else ""
                print(f"  {f}:{no}  [{level}] {kind}：「{hit}」→ {good}{tail}")
        total_err += sum(1 for x in findings if x[1] == "錯誤")
        total_warn += sum(1 for x in findings if x[1] != "錯誤")

        if placeholders and not args.no_placeholder and not args.errors_only:
            print(f"\n--- {f} 待填清單（{len(placeholders)} 處）---")
            for no, content in placeholders:
                print(f"  {f}:{no}  {content}")
        total_ph += len(placeholders)

    print(f"\n合計：錯誤 {total_err}、建議 {total_warn}、待填 {total_ph}"
          f"（另有 {total_skip} 行標記略過）")
    if total_err:
        print("有[錯誤]項目，交件前務必修正。")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
