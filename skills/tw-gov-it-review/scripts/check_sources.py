#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
官方來源查證：比對本組 skill 引用的政府文件頁面是否已改版。

用法：
    python scripts/check_sources.py                # 逐項連線比對
    python scripts/check_sources.py --list         # 只列清單，不連線
    python scripts/check_sources.py --只看異動     # 只列需人工確認的項目
    python scripts/check_sources.py --嚴格         # 連不上也視為未通過（送件前用）
    python scripts/check_sources.py --timeout 30   # 調整逾時秒數（預設 20）

清單不寫在本檔內，一律讀 references/04-來源與查證.md 中標記【來源清單】的表格，
避免兩邊不一致。要新增或修改來源請改該檔。

比對方式依「識別字串」欄的形態分兩種：

1. 民國七位日期（如 1150727）——**比大小**。工程會範本頁面是新版在前、
   歷史版本並列，單純搜尋字串永遠找得到，偵測不到改版；因此改為掃出頁面上
   所有合法的民國日期取最大值，只要出現比記載更新的日期就報 [異動]。
2. 其他（發文字號、文件名稱等）——**找字串**，找不到即報 [異動]。

    [相符]   未發現更新版本
    [異動]   頁面上有更新的版本，或識別字串已消失——請人工開啟確認
    [無法連線] 逾時、HTTP 錯誤或 DNS 失敗

**腳本不判斷新版本的內容差異，只負責提醒你去看。** 走字串比對的項目，
[相符] 僅表示「無須優先處理」而非「已確認為現行版」（頁面可能同時列出
歷史版本）。真正要引用版本號時仍須人工開啟頁面確認。

僅使用標準函式庫，不需額外安裝套件。

連線逾時會自動重試一次。**[無法連線] 不等於沒有異動**，那幾項這次並未查證到；
預設離開碼仍為 0（政府網站偶有維護，不該讓排程紅燈），送件前查證請加 `--嚴格`。

離開碼：0 無異動／1 有[異動]／2 僅在 --嚴格 下表示有來源連不上。
"""
import argparse
import gzip
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SOURCES_DOC = Path(__file__).resolve().parent.parent / "references" / "04-來源與查證.md"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def build_ssl_context() -> ssl.SSLContext:
    """
    仍驗證憑證鏈與主機名稱，但關閉 VERIFY_X509_STRICT。

    Python 3.13 起預設啟用嚴格的 RFC 5280 檢查，多個政府網站的憑證因缺少
    Subject Key Identifier 而被判定失敗（Missing Subject Key Identifier）。
    這是憑證簽發格式的問題，不是連線遭竄改，關閉此旗標即可正常查證。
    """
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def encode_url(url: str) -> str:
    """路徑或查詢字串含中文時先百分比編碼，否則 http.client 會以 ascii 編碼失敗。"""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        parts.scheme,
        parts.netloc.encode("idna").decode("ascii") if any(
            ord(c) > 127 for c in parts.netloc) else parts.netloc,
        urllib.parse.quote(parts.path, safe="/%"),
        urllib.parse.quote(parts.query, safe="=&%"),
        parts.fragment,
    ))


def parse_sources(path: Path):
    """讀取標記【來源清單】的表格。回傳 [(名稱, 版本, 識別字串, 網址, 查證日期)]。"""
    rows = []
    if not path.exists():
        return rows
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            active = "【來源清單】" in line
            continue
        if not active or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[0] == "文件名稱" or set(cells[0]) <= set("-: "):
            continue
        name, version, token, url, checked = (c.replace("**", "") for c in cells[:5])
        if not url.startswith("http"):
            continue
        rows.append((name, version, token, url, checked))
    return rows


def fetch(url: str, timeout: int, ctx: ssl.SSLContext) -> str:
    req = urllib.request.Request(encode_url(url), headers={
        "User-Agent": UA,
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


ROC_DATE = re.compile(r"(?<!\d)(1[0-4]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)")


def latest_roc_date(text: str) -> str:
    """
    掃出頁面上所有合法的民國七位日期，回傳最大者；沒有則回傳空字串。

    年份限 100~149、月份 01~12、日 01~31，可濾掉檔案大小等雜訊數字。
    前後不得再接數字，避免從發文字號（如 1120022701）中截出假日期。
    """
    found = [m.group(0) for m in ROC_DATE.finditer(text)]
    return max(found) if found else ""


def normalise(text: str) -> str:
    """去掉 HTML 標籤與空白，讓跨標籤切斷的字串也能比對到。"""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text,
                  flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", "", text)


def fetch_with_retry(url: str, timeout: int, ctx: ssl.SSLContext) -> str:
    """政府網站偶有短暫逾時，重試一次再判定為無法連線。"""
    try:
        return fetch(url, timeout, ctx)
    except Exception:
        return fetch(url, timeout, ctx)


def check(rows, timeout: int, changed_only: bool):
    changed = unreachable = 0
    ctx = build_ssl_context()
    for name, version, token, url, checked in rows:
        try:
            body = normalise(fetch_with_retry(url, timeout, ctx))
        except Exception as exc:  # 單一來源連不上時不中斷整批查證
            unreachable += 1
            reason = getattr(exc, "reason", None) or exc
            print(f"[無法連線] {name}\n            {type(exc).__name__}: {reason}"
                  f"\n            {url}")
            continue

        token = token.replace(" ", "")

        if token in ("—", "-", ""):
            if not changed_only:
                print(f"[相符]   {name}（僅確認可連線）")
            continue

        if ROC_DATE.fullmatch(token):
            newest = latest_roc_date(body)
            if not newest:
                hit, detail = False, "頁面上找不到任何版本日期，版面可能已改"
            elif newest > token:
                hit, detail = False, f"頁面上已有更新的版本日期 {newest}"
            else:
                hit, detail = True, ""
        else:
            hit = token in body
            detail = f"頁面已找不到「{token}」"

        if hit:
            if not changed_only:
                print(f"[相符]   {name}：{version}")
        else:
            changed += 1
            print(f"[異動]   {name}")
            print(f"            本專案記載：{version}（查證日期 {checked}）")
            print(f"            {detail}，請人工確認現行版本")
            print(f"            {url}")
    return changed, unreachable


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--list", action="store_true", help="只列清單，不連線")
    ap.add_argument("--只看異動", dest="changed_only", action="store_true")
    ap.add_argument("--timeout", type=int, default=20, help="連線逾時秒數（預設 20）")
    ap.add_argument("--嚴格", dest="strict", action="store_true",
                    help="有來源連不上時也以離開碼 2 回報（送件前查證建議加）")
    args = ap.parse_args()

    rows = parse_sources(SOURCES_DOC)
    if not rows:
        sys.exit(f"讀不到來源清單：{SOURCES_DOC}")

    if args.list:
        print(f"來源清單（共 {len(rows)} 項，取自 {SOURCES_DOC.name}）：\n")
        for name, version, token, url, checked in rows:
            print(f"  {name}")
            print(f"    版本：{version}（查證日期 {checked}）")
            print(f"    網址：{url}\n")
        return 0

    print(f"比對 {len(rows)} 項官方來源……\n")
    changed, unreachable = check(rows, args.timeout, args.changed_only)
    print()
    if changed:
        print(f"有 {changed} 項需人工確認。確認後請更新 "
              f"references/04-來源與查證.md 的版本、識別字串與查證日期，"
              f"並同步 references/03-法規速查.md 與 README.md。")
        return 1
    if unreachable:
        # 連不上不等於沒異動。送件前查證要看到這一行，不能當成全綠。
        print(f"其餘未發現異動，但有 {unreachable} 項連不上，"
              f"**這幾項這次沒有查證到**，請稍後重跑或人工開啟確認。")
        return 2 if args.strict else 0
    print("未發現異動。（[相符] 僅表示無須優先處理，引用版本號前仍請人工確認。）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
