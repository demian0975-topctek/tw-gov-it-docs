# 倉庫慣例

只寫「讀程式碼看不出來、但寫錯會出事」的規矩。內容面的規範看 `README.md`，
兩個 skill 各自的用法看它們的 `SKILL.md`。

## 路徑一律相對於 skill 根目錄

`references/`、`assets/`、`scripts/` 底下的檔案在引用其他檔案時，**路徑是相對於
該 skill 的根目錄（SKILL.md 所在處），不是相對於檔案自己的位置**。

```
references/07-機關端工作說明書.md 裡要指向同 skill 的 assets：
  assets/00-共通元件.md                      ← 對
  ../assets/00-共通元件.md                   ← 錯

要指向另一個 skill：
  ../tw-gov-it-review/references/03-法規速查.md      ← 對
  ../../tw-gov-it-review/references/03-法規速查.md   ← 錯
```

這是因為這些檔案會被組進 STANDALONE.md，也會被 skill 執行環境從根目錄載入。
新增檔案後值得驗一次所有連結解析得開。

## STANDALONE.md 是產物，不要手改

`skills/*/STANDALONE.md` 由 `tools/build_standalone.py` 從 SKILL.md ＋
references ＋ assets 組出來，供上傳到 ChatGPT、Gemini 這類沒有檔案系統的環境。

改過任何分檔後必跑：

```bash
python tools/build_standalone.py          # 重建
python tools/build_standalone.py --check  # 驗證是否為最新（離開碼可用於 CI）
```

## 版面規格只存在範本裡，不要抄進腳本

`skills/tw-gov-ta-docs/assets/工作說明書範本.docx` 是產物，由 `tools/make_template.py`
從結案案例 Word 檔萃取（來源檔是真實案件，不進倉庫，路徑由執行者自備）。

字體、字級、縮排、行距、頁面邊界、頁首頁尾、五層自動標號全部住在範本的 `styles.xml`
與 `numbering.xml` 裡。`make_docx.py` 只掛樣式，**不要為了「調一下版面」在腳本裡寫
Pt/Twips 數值**——那會變成兩份互相矛盾的版面規格，而 Word 開檔時以範本為準，腳本裡
那份永遠看不出有沒有生效。要改版面就改範本後重跑 `make_template.py`。

同理，標號是 Word 的自動編號，**不要在骨架 Markdown 或腳本裡把「壹、」當文字寫進
Word**。骨架裡的標號只給人讀，`make_docx.py` 會剝掉再交給 Word 編。改完跑
`skills/tw-gov-ta-docs/scripts/check_outline.py <產出.docx>` 驗大綱有無跳層。

## 規則寫在表格，腳本只負責解析

`check_wording.py` 的用字規則在 `references/02-用語與表達.md` 的【檢查規則】表格裡；
`check_sources.py` 的來源清單在 `references/04-來源與查證.md` 的【來源清單】表格裡；
`check_layout.py` 的版面判定值在 `references/06-Word範本.md` 的【版面檢查值】表格裡。

**不要把規則寫進 .py**。要改規則改表格，人看得到、腳本讀得到，只有一份。
新增這類腳本時沿用同樣的寫法。

## 交出去之前

```bash
python skills/tw-gov-it-review/scripts/check_wording.py --只看錯誤 <改過的檔案>
python skills/tw-gov-it-review/scripts/check_sources.py --只看異動 --嚴格
python tools/build_standalone.py && python tools/build_standalone.py --check
```

動過任一支產 Word 的腳本、骨架或範本時，**產一份出來驗**——版面與標號的錯誤不會讓腳本
失敗，只會安靜地產出格式壞掉的檔案：

```bash
# tw-gov-it-docs：版面由腳本自己產，驗規範值
python skills/tw-gov-it-docs/scripts/make_docx_skeleton.py 03 -o <暫存>/版面檢查.docx
python skills/tw-gov-it-docs/scripts/check_layout.py <暫存>/版面檢查.docx

# tw-gov-ta-docs：版面住在範本裡，驗有沒有偏離範本，並確認大綱逐層遞進
python skills/tw-gov-ta-docs/scripts/make_docx.py <骨架.md> <暫存>
python skills/tw-gov-ta-docs/scripts/check_outline.py <暫存>/工作說明書_V0.0.docx
python skills/tw-gov-it-docs/scripts/check_layout.py --範本 \
    skills/tw-gov-ta-docs/assets/工作說明書範本.docx <暫存>/工作說明書_V0.0.docx
```

最後那道是**維護端的把關，不是 skill 之間的依賴**——`tw-gov-ta-docs` 的使用者流程不跑它，
`SKILL.md` 裡也不會出現。倉庫維護者當然可以用倉庫裡任何一支腳本。

**兩個模式不能互換。** 預設模式比對「政府文書格式參考規範」的公文版面；`tw-gov-ta-docs`
的範本萃取自真實案件（四邊 2.0 公分、行距 20～24 點），與公文格式本來就不同，用預設模式
驗會得到上百個假警報。`--範本` 驗的才是上面那條規矩：腳本有沒有蓋掉範本的版面。

`check_layout.py` 驗的是 Word 繼承後的**有效值**（run → 段落 → 樣式 → Normal →
docDefaults）。只看段落上有沒有明確設定，會漏掉空白表格列——那正是使用者要填字的地方。

用字檢查有幾個字是**刻意不自動攔**的（紀錄／記錄、計畫／計劃、臺／台、程序、
登錄、界面），要看詞性與對象人工判斷，自動改一定會錯——判斷表在
`references/02-用語與表達.md`。

## 內容面三條硬規矩

寫進 skill 內容或範例時同樣適用，不只是產出文件時：

1. **不編造。** 技術數據、法規條號、人名、機關內部環境資訊，未知一律寫
   `【待填：○○】`。政府文件送出後不易更正，引錯要負責。
2. **不寫敏感資訊。** 真實 IP、網路架構、帳號密碼原則、資安設定值、開放埠清單
   都不進倉庫。依《行政院及所屬機關（構）使用生成式 AI 參考指引》，機密文書
   應由承辦人親自撰寫。
3. **機關版本優先。** 本倉庫的章節規格是通用底稿，與機關提供的附件不一致時
   以機關版本為準，不要拿底稿去否定機關的要求。

## 引用官方文件時

**寧可只寫法規全名而不寫版本，也不要寫錯版本。** 工程會範本改版頻繁——投標須知
範本近一年改了四次，本倉庫曾讓過時三年的版本號留著。

必須寫版本號時，以 `references/04-來源與查證.md` 為準並自行複查；查證後在該檔的
「查證紀錄」加一列。腳本的 `[相符]` 只代表無須優先處理，不代表已確認為現行版。

## 未決事項

見 `TODO.md`。動到那兩項之前先確認使用者的決定，別自行開工。
