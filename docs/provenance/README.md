# 開發期溯源資料

**這個資料夾不進 skill。** 裡面是維護者才需要的東西：查證過的 changelog、腳本的設計理由、
各節內容的依據來源。skill 目錄（`skills/*/`）只放執行期材料——使用者帶走 skill 時不該連同
「作者當初怎麼查到這件事」一起帶走，那是載入就要付的上下文成本，卻不改變產出。

判準只有一句：**這段話改變的是 agent 產出的內容（留在 skill），還是記錄了作者當初怎麼查到的（放這裡）？**

| 檔案 | 管轄 |
| --- | --- |
| `check_sources-設計.md` | `skills/tw-gov-it-review/scripts/check_sources.py` 的比對機制與識別字串挑法 |
| `tw-gov-it-review-04-查證紀錄.md` | `skills/tw-gov-it-review/references/04-來源與查證.md` 的歷次查證結果 |
| `tw-gov-it-docs-07-依據對照.md` | `skills/tw-gov-it-docs/references/07-機關端工作說明書.md` 各節的依據等級 |

**不要從 skill 檔案指向這裡。** 一旦 `SKILL.md` 或 `references/` 出現指向 `docs/` 的連結，
這些內容就又回到 agent 的可達範圍，而且 `STANDALONE.md` 組出來會是斷鏈。維護者從本檔進入即可。
