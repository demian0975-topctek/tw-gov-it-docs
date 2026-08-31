# Skill 瘦身研究：單檔、全檔加總、description、開發期產物分離

研究日期：2026-08-31。對象：`skills/tw-gov-it-docs`、`skills/tw-gov-it-review`、`skills/tw-gov-ta-docs`。

本檔是**研究筆記**，不是規範，也不改任何 skill 檔。所有非顯而易見的主張都附一手來源連結；查不到一手來源的另列於最後一節。

---

## 零、先看結論

| 軸 | 最高投報率的一件事 | 估計效益 |
| --- | --- | --- |
| description | 三份合計 996 字元 → 649 字元 | 每個 session 常駐省約 300 est. tokens |
| 單檔 | `tw-gov-it-docs/SKILL.md` 的 `assets/` 十四列表格 → 移進 `references/` 或改成一行指路 | 觸發時省約 700 est. tokens |
| 加總 | 三份 `SKILL.md` 重複四次的「不編造／不寫敏感／機關版本優先」收斂為單一來源 | 觸發時省約 250～400 est. tokens，且維護變成一處 |
| 開發期產物 | `STANDALONE.md` × 3（共 116 KB）與 `04-來源與查證.md` 的〈查證紀錄〉搬出 skill 目錄 | 執行期 0（見第七節第 3 小節），但發佈體積 −116 KB、維護面 −1 份重複 |

> **實際採用的結果（2026-08-31 執行後回填）**：description 三份合計 996 → **781** 字元，不是提案的 649。`tw-gov-it-review` 的壓縮版沒能通過驗收而維持原文——不是因為量到掉點，是因為這套量測法解析不了這個量級的差異，見 7-4。

**最重要的認知修正**：`STANDALONE.md` 雖然有 178 KB，**在 Claude Code 執行期不花任何上下文**，因為沒有任何 `SKILL.md` 指向它。它是發佈通道的問題與維護重複的問題，不是上下文的問題。真正每個 session 都在花錢的只有 `name` + `description`。

---

## 一、已查證的硬性限制與建議值

### 1-1 硬性限制（超過會被拒絕或截斷）

| 項目 | 值 | 性質 | 來源 |
| --- | --- | --- | --- |
| `name` 長度 | 最多 64 字元，僅小寫英數與連字號，不得含 XML tag，不得含保留字 `anthropic` / `claude` | 硬性 | [Skills overview §Skill structure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)、[agentskills.io Specification](https://agentskills.io/specification) |
| `description` 長度 | 最多 **1,024 字元**，不得為空，不得含 XML tag | 硬性（spec 與 API） | 同上 |
| `compatibility` 長度 | 最多 500 字元 | 硬性 | [agentskills.io Specification](https://agentskills.io/specification) |
| Claude Code skill listing **每筆**上限 | `description` ＋ `when_to_use` **合計 1,536 字元**後截斷 | 硬性（Claude Code 端，可用 `skillListingMaxDescChars` 調整） | [Claude Code Skills §Frontmatter reference](https://code.claude.com/docs/en/skills) |
| Claude Code skill listing **總**預算 | 模型 context window 的 **1%**（字元計），溢出時**從最少用的 skill 開始整筆丟掉 description** | 硬性（可用 `skillListingBudgetFraction` 或 `SLASH_COMMAND_TOOL_CHAR_BUDGET` 調整） | [Claude Code Skills §Skill descriptions are cut short](https://code.claude.com/docs/en/skills) |
| Skill 上傳總體積 | 未壓縮 **30 MB** 以下 | 硬性（API / claude.ai 上傳） | [Using Agent Skills with the API](https://platform.claude.com/docs/en/build-with-claude/skills-guide) |
| 單一 request 可帶入的 skill 數 | 20 | 硬性（API） | 同上 |

> **關鍵：Claude Code 的兩道 description 限制是「字元」不是「token」。** 這對 CJK 是**有利**的——同樣 1,536 字元，中文承載的資訊量遠大於英文。詳見第六節。

### 1-2 軟性建議（Anthropic 官方建議，非強制）

| 項目 | 建議值 | 來源 |
| --- | --- | --- |
| `SKILL.md` body 行數 | **500 行以下**（"Keep SKILL.md body under 500 lines for optimal performance"） | [Best practices §Token budgets](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |
| Level 2（`SKILL.md` body）token 量 | **Under 5k tokens** | [Skills overview 三層表格](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| Level 1（metadata）token 量 | **~100 tokens per Skill** | 同上 |
| reference 檔超過 100 行 | 加目錄（table of contents），因為 Claude 可能只 `head -100` 預覽 | [Best practices §Structure longer reference files](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |
| reference 檔超過 300 行 | 加目錄 | [anthropics/skills `skills/skill-creator/SKILL.md`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) |
| 引用深度 | **一層**（"Keep references one level deep from SKILL.md"），巢狀引用會導致 Claude 只做部分讀取 | [Best practices §Avoid deeply nested references](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |

### 1-3 本倉庫的現況對照

三份 `SKILL.md` 全部遠低於 500 行（132／81／57 行）。**行數不是本倉庫的瓶頸，token 密度才是**——CJK 每字元約產生 1 個 token，`tw-gov-it-docs/SKILL.md` 的 5,899 字元（3,380 個 CJK 字）估算約 4,085 tokens，已逼近官方 Level 2 的「under 5k tokens」建議上限。

---

## 二、載入模型：哪些位元組永遠在上下文

這一節決定其餘所有建議是否成立，逐條附一手來源。

### 2-1 三層模型（官方原文）

[Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) 的表格逐字如下：

| Level | When loaded | Token cost | Content |
| --- | --- | --- | --- |
| Level 1: Metadata | Always (at startup) | ~100 tokens per Skill | `name` and `description` from YAML frontmatter |
| Level 2: Instructions | When Skill is triggered | Under 5k tokens | SKILL.md body with instructions and guidance |
| Level 3+: Resources | As needed | None until accessed | Bundled files. Reference files load into context when read. Scripts run through bash, and only their output enters context |

### 2-2 逐項確認

- **永遠在上下文**：**每一個已安裝 skill** 的 `name` + `description`。
  > "At startup, only the metadata (name and description) from all Skills is pre-loaded."
  > — [Best practices §Concise is key](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

  Claude Code 版本的說法更精確：預設狀態是 "Description always in context, full skill loads when invoked"；設 `disable-model-invocation: true` 則 "Description not in context"（[Claude Code Skills](https://code.claude.com/docs/en/skills)）。

- **觸發時才載入**：`SKILL.md` 的 body。
  > "When you request something that matches a Skill's description, Claude reads SKILL.md from the filesystem using bash. Only then does this content enter the context window."
  > — [Skills overview §Level 2](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

  Claude Code 另有一項本倉庫需要注意的機制：
  > "the rendered `SKILL.md` content enters the conversation as a single message and stays there across later turns. […] Claude Code does not re-read the skill file on later turns"
  > — [Claude Code Skills](https://code.claude.com/docs/en/skills)

  意思是 `SKILL.md` 的成本是**一次性但整段常駐到 session 結束**，不是每 turn 重新計費，也不會自動刷新。

- **只有被讀到才計費**：`references/`、`assets/`。
  > "Reference files, data, or documentation don't consume context tokens until actually read."
  > "The sales.md and product.md files remain on the filesystem, consuming zero context tokens until needed."
  > — [Best practices §Runtime environment](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

- **執行但不載入**：`scripts/`。
  > "When Claude runs `validate_form.py`, the script's code never loads into the context window. Only its output […] consumes tokens."
  > — [Skills overview §The Skills architecture](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

  這對本倉庫很重要：`scripts/make_docx_skeleton.py`（18 KB）、`check_layout.py`（17 KB）、`check_wording.py`（15 KB）**加起來 50 KB，執行期成本為零**，只要 `SKILL.md` 明確寫「run」而不是「see」。官方特別要求把意圖寫清楚：
  > "Run `analyze_form.py` to extract fields" (execute) vs "See `analyze_form.py` for the extraction algorithm" (read as reference)

  本倉庫三份 `SKILL.md` 全部用的是「跑」「python scripts/...」的執行語氣，**這一點已經做對了**。

### 2-3 本倉庫的實際帳（估算）

估算法：CJK 字元 × 1.0 ＋ 非 CJK 字元 × 0.28。**這是估算不是量測**，理由與量測方式見第八節與第九節。

| 檔案 | 行 | 字元 | CJK | est. tokens | 何時計費 |
| --- | --- | --- | --- | --- | --- |
| 三份 description 合計 | — | 996 | 738 | **~810** | **每個 session 常駐** |
| `tw-gov-it-docs/SKILL.md` | 132 | 5,899 | 3,380 | 4,085 | 觸發時 |
| `tw-gov-it-review/SKILL.md` | 81 | 2,812 | 1,685 | 2,000 | 觸發時 |
| `tw-gov-ta-docs/SKILL.md` | 57 | 1,812 | 1,013 | 1,236 | 觸發時 |
| 全部 `references/` ＋ `assets/`（22 檔） | — | — | — | ~74,400 | 讀到才計費 |
| 全部 `scripts/`（6 支，約 68 KB） | — | — | — | **0** | 執行不載入 |
| `STANDALONE.md` × 3 | 3,994 | 116,689 | — | ~81,800 | **0**（無人指向，見第七節） |

**這張表就是整份研究的地圖。** 每個 session 都在付的只有 810 est. tokens；觸發時才付的是 1,236～4,085；其餘 15 萬 tokens 的內容全部是「用到才付」。

---

## 三、軸一：單文件瘦身

依投報率排序。每項都指到本倉庫的實際檔案與行號。

### 3-1【高】`tw-gov-it-docs/SKILL.md` 的兩張路由表，只留一張

`SKILL.md:33-43` 是 references 路由表（9 列），`SKILL.md:51-66` 是 assets 骨架表（14 列）。兩張表合計約 1,700 字元、約 1,200 est. tokens，占該檔近 30%。

官方的 progressive disclosure Pattern 1／Pattern 2 示範的路由段落都只有四到五行（[Best practices §Progressive disclosure patterns](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)）。`assets/` 那 14 列的內容是「檔名 → 這份文件叫什麼」——**檔名本身已經寫著答案**（`assets/03-需求規格書骨架.md` 的用途欄寫「SRS」）。這正是外部撰寫規範說的 cache：

> "The **environment** is a source of truth too […] and a document that restates it is a **cache** […] Leave the one-file, one-command lookups to the environment"
> — 撰寫規範 `writing-for-agents`〈Pruning〉節（倉庫外部材料，不隨本倉庫散布）

做法：14 列縮成 3～4 行，只保留檔名看不出來的資訊（`00-共通元件` 每份都會用到、`07-系統管理手冊` 敏感度最高、`10-上線切換` App 不適用、`13-工作說明書` 是機關端）。其餘讓 agent `ls assets/` 自己看。

估計省 **~700 est. tokens**。

### 3-2【高】刪掉模型本來就會做的句子（no-op 獵殺）

外部撰寫規範的檢驗法是「這句話有沒有改變預設行為」，且要求**整句刪掉而不是修短**。官方也是同一句話：

> "Only add context Claude doesn't already have. Challenge each piece of information: 'Does Claude really need this explanation?'"
> — [Best practices §Concise is key](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

本倉庫的候選（皆為判斷，需逐句跑 no-op 測試確認）：

| 位置 | 內容 | 為什麼可能是 no-op |
| --- | --- | --- |
| `tw-gov-it-docs/SKILL.md:8` | 「協助廠商（或機關承辦人）產出符合…的資訊系統開發文件。」 | 身分陳述；`description` 已載明，外部撰寫規範明說 "Cut identity that's already in the body"，其反向也成立：body 不必重述 description |
| `tw-gov-it-docs/SKILL.md:10` | 「這類文件的評分者不是工程師，而是評選委員與驗收小組…」整段 | 動機說明。但末句「本 skill 的核心不是把文件寫得漂亮，而是把**可追溯性**與**章節完整性**做到位」是 leading word，**要留** |
| `tw-gov-it-docs/SKILL.md:84` | 「章節缺漏在驗收時是硬傷，比內容寫得普通嚴重得多。」 | 理由句，指令已在前一句 |
| `tw-gov-it-docs/SKILL.md:131` | 「本 skill 產出的是初稿。正式送件前仍須經廠商內部覆核與機關承辦人確認，AI 不取代投標與履約的正式程序。」 | 免責聲明，不改變 agent 行為（三份 `SKILL.md` 各有一句同類） |
| `tw-gov-it-review/SKILL.md:61` | 「報告要能讓使用者直接改，所以：」 | 下面四點自己會說明 |

估計三份合計省 **~400～600 est. tokens**。

### 3-3【中】把散文改成腳本輸出

官方立場：
> "Even if Claude could write a script, pre-made scripts offer advantages: […] Save tokens (no need to include code in context)"
> — [Best practices §Provide utility scripts](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

本倉庫已經把三組規則表交給腳本解析（`CLAUDE.md`「規則寫在表格，腳本只負責解析」），**這個模式是對的且與官方一致**。可以再往前走一步的是：`references/06-Word範本.md:70` 的【版面檢查值】表格目前同時被人與 `check_layout.py` 讀。若 agent 從不需要肉眼比對這張表（只需要跑腳本看輸出），這張表可以移到腳本旁的資料檔，`SKILL.md`／reference 只留一行「跑 `check_layout.py`」。

**先量測再動**：這一項會犧牲單檔版（ChatGPT／Gemini）使用者的可用性，因為那邊沒有腳本可跑。權衡見第七節第 4 小節。

### 3-4【中】長 reference 檔加目錄

超過 100 行的 reference 都適用（[Best practices §Structure longer reference files](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)）。本倉庫超過 100 行的有 9 個檔，最長的是 `tw-gov-it-review/references/01-結構與格式.md`（274 行）與 `tw-gov-it-docs/references/04-履約與維運文件.md`（245 行）。

這一項**不省 token，而是防漏讀**——官方明說 Claude 可能用 `head -100` 預覽，沒有目錄就會拿到不完整資訊。加目錄會讓檔案略微變大但讓「只讀需要的那一節」變可行，淨效果是省。

### 3-5【低】description 裡的 Markdown 粗體

`tw-gov-it-docs` 的 description 用了 4 組 `**…**`（32 個字元）。skill listing 是純文字比對，且 Claude Code 會對 description「escapes angle brackets so the text can't imitate Claude Code's internal formatting」（[Claude Code Skills](https://code.claude.com/docs/en/skills)）。官方六份範例 skill 的 description 全部沒有 Markdown 標記（見第六節第 3 小節）。**沒有一手來源說粗體會提高命中率**，但確定會占字元。刪。

---

## 四、軸二：全部檔案加總瘦身

### 4-1【高】三份 `SKILL.md` 重複的「三條硬規矩」

同一個意思出現在四個地方：

| 位置 | 段落 |
| --- | --- |
| `skills/tw-gov-it-docs/SKILL.md:125-131` | 〈重要提醒〉 |
| `skills/tw-gov-it-review/SKILL.md:68-72` | 〈這幾項不要自己動手改〉 |
| `skills/tw-gov-ta-docs/SKILL.md:44-50` | 〈這幾項不要自己動手改〉 |
| `CLAUDE.md`〈內容面三條硬規矩〉 | 給維護者的版本 |

驗證：`生成式 AI 參考指引` 在三份 `SKILL.md` ＋ `CLAUDE.md` 各出現一次；`機關版本` 出現 6 次；`編造` 出現 6 次。

外部撰寫規範對此的判定是明確的：
> "**Duplication** — the same meaning in more than one place — costs maintenance and tokens, and inflates a meaning's prominence on the ladder past its real rank."
> — 撰寫規範 `writing-for-agents`〈Pruning〉節（倉庫外部材料，不隨本倉庫散布）

**但這裡有一個真實的張力，不要無腦收斂。** 三個 skill 是「各自獨立、彼此不互相依賴」（`tw-gov-ta-docs/SKILL.md:3` 的 description 明文承諾），把三條規矩抽成共用檔會製造依賴，違反該承諾，也違反官方的一層引用原則。

務實做法（三選一，需要人決策）：

1. **維持三份，但各自壓到 2～3 行**：只留「做什麼」不留「為什麼」。三段目前各約 250～400 字元，可壓到約 120 字元。省 ~250～400 est. tokens，且不製造依賴。**建議先做這個。**
2. 抽成第四個 `disable-model-invocation: true` 的共用 skill：零 context load，但每個 skill 都得指過去 → 製造依賴，且單檔版（STANDALONE）會缺席。不建議。
3. 只留在觸發率最高的那一份：會讓另兩份少掉硬規矩。不建議。

### 4-2【中】跨 skill 的邊界說明重複

「公文書（函、令、公告）／發文字號判準／tw-formal-writing 連結」同時出現在 `tw-gov-it-docs/SKILL.md:108-116` 與 `tw-gov-it-review/SKILL.md:74-80`，兩處都約 300 字元。判準句「這份文件會不會用機關發文字號發出去？」是很好的 leading word，兩邊都該留；**但 tw-formal-writing 的 GitHub 網址與「履約期間行文給機關…」的細節只需要一處**。

### 4-3 行級重複已經很乾淨

跨檔掃描（不含 `STANDALONE.md`）只找到 3 條長度 ≥24 字元的重複行：追溯鏈那一行、`【封面】【文件版本紀錄表】【目錄…】` 在 6 個骨架裡、以及一行 `check_wording.py` 指令。**這代表本倉庫的行級去重已經做得很好，剩下的是「同一個意思用不同句子寫」的語意級重複**（4-1、4-2）。

### 4-4 `assets/` 與 `references/` 的加總不是問題

22 個檔約 74,400 est. tokens，但**只有被讀到的那一兩個會計費**。官方明說：
> "**Bundle comprehensive resources:** Include complete API docs, extensive examples, large datasets; no context penalty until accessed"
> — [Best practices §Runtime environment](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

真正要控的是**單一 reference 檔的大小**（因為讀進去就是整檔），不是總量。目前最大的 `04-履約與維運文件.md` 約 7,000 est. tokens——讀一次就吃掉 Level 2 建議上限的 1.4 倍。若使用者只是要查 SLA 一節，這是浪費。可考慮的做法是 Pattern 2 的 domain 拆分（把「資料移轉／上線切換／交接／月報 SLA／履約管理」拆成獨立小檔），代價是 `SKILL.md` 的路由表變長——與 3-1 直接衝突。**兩害相權，建議先做 3-4（加目錄）而非拆檔**，因為目錄讓 agent 可以只讀需要的那一節。

---

## 五、軸三：description 壓縮

### 5-1 description 是怎麼被用來比對的（一手來源）

- 它被注入 system prompt：
  > "**Always write in third person**. The description is injected into the system prompt, and inconsistent point-of-view can cause discovery problems."
  > — [Best practices §Writing effective descriptions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- 它是**選 skill 的依據**，不只是「要不要用」：
  > "The description is critical for skill selection: Claude uses it to choose the right Skill from potentially 100+ available Skills."
  > — 同上
- 它要同時回答「做什麼」與「什麼時候用」，並要含具體關鍵詞：
  > "**Be specific and include key terms**. Include both what the Skill does and specific triggers/contexts for when to use it."
  > — 同上
- Anthropic 自己的 skill-creator 進一步指出模型**傾向不觸發**，所以 description 要「pushy」：
  > "currently Claude has a tendency to 'undertrigger' skills -- to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit 'pushy'."
  > — [anthropics/skills `skills/skill-creator/SKILL.md`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- 而且觸發本身有門檻，與 description 無關：
  > "Claude only consults skills for tasks it can't easily handle on its own — simple, one-step queries […] may not trigger a skill even if the description matches perfectly"
  > — 同上

**推論**：壓縮 description 的安全邊界是「刪掉不做觸發工作的字」——身分陳述、機制說明、連接詞、修辭——而**保留每一個使用者可能真的打出來的名詞**。

### 5-2 CJK vs 英文：兩個方向相反的效應

| 面向 | 中文 description | 英文 description |
| --- | --- | --- |
| Claude Code 的 1,536 字元／筆上限與 1% 字元總預算 | **有利**：同樣字元數承載更多資訊 | 不利 |
| 實際 context token 成本 | **不利**：CJK 約 1 token/字元 | 有利：約 0.25 token/字元 |
| 觸發命中率 | 未查證 | 未查證 |

**有沒有官方說法建議 description 用哪種語言？沒有查到。** 官方只規定第三人稱與「include key terms」，沒有任何語言偏好的陳述。本倉庫的使用者說中文、打的是中文名詞（「需求規格書」「工作說明書」「退件」），把這些關鍵詞換成英文會直接損失字面比對機會，**因此建議維持中文**——但這是推論，不是查證。若要驗證，唯一可靠的方式是第八節的 description tuning 迴圈（實測 trigger rate），不是猜。

### 5-3 官方範例的 description 長度與句法（校準基準）

從 [anthropics/skills](https://github.com/anthropics/skills) 逐字取得：

| skill | description 字元數 | 句法特徵 |
| --- | --- | --- |
| `brand-guidelines` | ~230 | 一句「做什麼」＋ 一句 "Use it when…" |
| `mcp-builder` | ~275 | 同上 |
| `skill-creator` | ~296 | 同上，"Use when users want to A, B, or C" |
| `pdf` | ~410 | 動詞清單枚舉 ＋ "If the user mentions a .pdf file or asks to produce one, use this skill." |
| `docx` | ~833 | 枚舉 ＋ "Triggers include: …" ＋ **"Do NOT use for PDFs, spreadsheets, Google Docs…"** |
| `xlsx` | ~975 | 枚舉 ＋ 副檔名別名清單 ＋ **"Do NOT trigger when the primary deliverable is a Word document…"** |

**兩個可直接借用的官方寫法**：

1. **副檔名／別名清單是被官方接受的**——`xlsx` 列了 `.xlsx, .xlsm, .xltx, .csv, .tsv`。所以本倉庫列「需求規格書 SRS」「設計規格書 SDD（SA／SD）」不是浪費，是必要的別名。
2. **`Do NOT use for X` 的負向路由句是官方寫法**。`writing-for-agents:74` 主張避免 negation（"Prompt the **positive**"），但那條規則的對象是**body 的行為指令**；官方在有多個易混淆姊妹 skill 時，description 裡明確寫排除項。本倉庫有三個高度相似的姊妹 skill，**負向路由句要保留**，只是可以更短。

### 5-4 三份改寫（逐字）

估算法同第二節。三份現況都**遠低於 1,024 硬上限與 1,536 截斷點**，所以**目前沒有被截斷的風險**——這次壓縮的收益是 token 與精準度，不是避免截斷。這一點要說清楚，免得誤以為是在解一個急迫的 bug。

---

#### (1) `tw-gov-it-docs`

**現況**（`skills/tw-gov-it-docs/SKILL.md:3`）：466 字元（348 CJK），est. **381 tokens**

> 台灣政府機關資訊系統委外案的文件撰寫：把需求追溯鏈從 RFP 一路接到測試案例。涵蓋投標階段的服務建議書、需求回應與規格符合對照表、評選簡報大綱；履約階段的專案執行計畫書、需求規格書與設計規格書（SRS／SDD，或稱 SA／SD 文件）、測試計畫與報告、使用手冊、系統管理手冊、教育訓練教材、期中期末與結案報告、需求變更與履約管理文件；上線與維運階段的資料移轉計畫、系統上線切換計畫、營運交接文件、維護月報與 SLA 服務水準報表。機關端要發包，這裡也有工作說明書（需求說明書、建議書徵求文件 RFP）與評選項目配分表。也涵蓋採購型態差異（最有利標與最低標、共同供應契約、雲端服務採購、開口契約、維護服務採購、AI 專案），並可產出各文件的 Word 空白範本。使用者提到政府標案、機關委外、需求說明書或系統驗收時使用；另一個 skill 需要各文件的通用章節規格時也讀這裡。\*\*文件已寫好、要在送件前挑出退件問題\*\*，用 tw-gov-it-review。\*\*不處理公文書\*\*（函、令、公告、開會通知單）與存證信函、陳情書、合約。

**提案**：275 字元（192 CJK），est. **215 tokens**（−41% 字元、−44% est. tokens）

> 台灣政府機關資訊系統委外文件撰寫。文件類型：服務建議書、規格符合對照表、專案執行計畫書、需求規格書 SRS、設計規格書 SDD（SA／SD）、測試計畫與報告、使用手冊、系統管理手冊、期中期末與結案報告、資料移轉計畫、上線切換計畫、營運交接文件、維護月報與 SLA、機關端工作說明書（需求說明書、RFP）與評選配分表，並產出 Word 空白範本。使用者提到政府標案、機關委外、需求說明書、交付文件或系統驗收時使用；另一個 skill 需要通用章節規格時也讀這裡。文件已寫好要挑退件問題用 tw-gov-it-review；公文書（函、令、公告）不處理。

**保留了什麼、為什麼**

| 保留 | 理由 |
| --- | --- |
| 全部文件名詞（服務建議書、需求規格書、SRS、SDD、SA／SD、測試、手冊、報告、移轉、切換、交接、SLA、工作說明書、RFP、配分表） | 使用者實際會打的字串；官方 `xlsx` 範例同樣保留別名清單 |
| 「使用者提到政府標案、機關委外、需求說明書、交付文件或系統驗收時使用」 | 官方要求的 "when to use" 觸發句；另加「交付文件」補一個常見說法 |
| 「另一個 skill 需要通用章節規格時也讀這裡」 | reach clause，`writing-for-agents:28` 明列為 description 該留的東西 |
| 兩句負向路由（→ review、公文書） | 三個姊妹 skill 的消歧義；官方 `docx`／`xlsx` 同樣寫法 |

**刪了什麼、為什麼**

| 刪除 | 理由 |
| --- | --- |
| 「把需求追溯鏈從 RFP 一路接到測試案例」（33 字元） | 機制說明，不是觸發詞。body `SKILL.md:10, 74-81` 已完整說明 |
| 「投標階段／履約階段／上線與維運階段」三個分段標籤（約 30 字元） | 結構修辭；名詞本身就是觸發詞，階段標籤不是 |
| 「需求回應與…評選簡報大綱」「教育訓練教材」「需求變更與履約管理文件」（約 30 字元） | 低頻長尾。**這是本次唯一有命中率風險的刪除**，若實測掉點就加回，成本僅 30 字元 |
| 採購型態整段括號枚舉（最有利標、共同供應契約、雲端服務採購、開口契約、維護服務採購、AI 專案，約 60 字元） | 這些不是使用者請求的**起點**，而是進到 skill 之後由 `references/05-採購型態.md` 分流的內部分支 |
| 「建議書徵求文件 RFP」→「RFP」、「開會通知單／存證信函／陳情書／合約」（約 25 字元） | 同一分支的同義詞；`writing-for-agents:16`「One trigger per branch」 |
| 4 組 `**` 粗體（32 字元） | 見 3-5 |

---

#### (2) `tw-gov-it-review`

**現況**（`skills/tw-gov-it-review/SKILL.md:3`）：345 字元（271 CJK），est. **292 tokens**

> 台灣政府機關資訊系統委外文件的退件風險審查：文件已經寫好，在送件或交付前逐項挑出會被機關退回的問題。兩類審查——結構與格式（章節缺漏、目錄與版本紀錄表、階層編號與圖表編號、需求到測試的追溯鏈斷點、交付檔案格式 ODF／PDF 與版面規格）；用詞用語與表達方式（簡體字、中國大陸用語、法律統一用字、無法驗收的模糊字眼、行銷形容詞、標點與全半形、序數的數字用法、已停止適用的法規名稱）。適用服務建議書、需求規格書、設計規格書、測試文件、各式手冊、期中期末與結案報告、資料移轉與上線切換計畫、營運交接文件、維護月報與 SLA 報表等技術文件。機關端公告前要自審工作說明書（需求說明書、RFP）也用這裡。要從頭撰寫請改用 tw-gov-it-docs；公文書（函、令、公告、開會通知單）不在範圍內。

**提案**：213 字元（161 CJK），est. **176 tokens**（−38% 字元、−40% est. tokens）

> 台灣政府機關資訊系統委外技術文件的送件前審查：文件已寫好，逐項挑出會被機關退回的問題。兩類——結構與格式（章節缺漏、目錄與版本紀錄表、階層與圖表編號、需求到測試的追溯鏈斷點、ODF／PDF 與版面規格）；用詞用語（簡體字、中國大陸用語、法律統一用字、無法驗收的模糊字眼、行銷形容詞、全半形標點、已停止適用的法規名稱）。機關端公告前自審工作說明書（RFP）也用這裡。要從頭撰寫用 tw-gov-it-docs；公文書不在範圍內。

**保留**：兩類檢查的具體項目清單。這些才是本 skill 的**判別性關鍵詞**——「簡體字」「中國大陸用語」「法律統一用字」「追溯鏈斷點」不會出現在另外兩個 skill 的請求裡。

**刪除的最大一塊**：整串文件類型清單（「適用服務建議書、需求規格書、設計規格書…等技術文件」，約 80 字元）。理由不只是省字：**這串名詞與 `tw-gov-it-docs` 的 description 幾乎完全重疊，是製造誤觸發的來源**。兩個 skill 的真正分界是動詞（審查／退件／送件前 vs 撰寫／產出），不是名詞。刪掉名詞、留下動詞，**理論上應該提升而非降低路由精準度**——但這是推論，屬於最該用第八節的 description tuning 實測的一項。

其餘刪除：「序數的數字用法」（低頻長尾，且被「用詞用語」涵蓋）、「交付檔案格式」「表達方式」等修飾語、`（函、令、公告、開會通知單）` 枚舉（「公文書」一詞已足）。

---

#### (3) `tw-gov-ta-docs`

**現況**（`skills/tw-gov-ta-docs/SKILL.md:3`）：185 字元（119 CJK），est. **137 tokens**

> 顧問或系統整合商受台灣政府機關委託、協助不熟悉資訊技術的機關撰寫工作說明書（需求說明書、RFP）草稿時使用。產出以機關第一人稱撰寫的 Word 草稿，機關專屬事實與每案不同的數字一律留白（○○○）交機關確認，不代為編造。與 tw-gov-it-docs（廠商或機關自行撰寫）、tw-gov-it-review（審查已寫好的文件）是各自獨立的 skill，彼此不互相依賴。

**提案**：161 字元（105 CJK），est. **121 tokens**（−13% 字元、−12% est. tokens）

> 顧問或系統整合商受台灣政府機關委託、協助不熟悉資訊技術的機關撰寫工作說明書（需求說明書、RFP）草稿時使用。產出以機關第一人稱撰寫的 Word 草稿，機關專屬事實與每案不同的數字留白（○○○）交機關確認，不代為編造。機關或廠商自行撰寫用 tw-gov-it-docs；審查已寫好的文件用 tw-gov-it-review。

**這一份本來就寫得好，壓縮空間最小。** 第一句同時完成「做什麼」「什麼時候用」與最關鍵的判別條件（**受委託代筆** vs 自行撰寫），是三份裡最接近官方範例句法的。

僅刪：「是各自獨立的 skill，彼此不互相依賴」（19 字元）——這是**給維護者看的事實**，對觸發判斷沒有作用（`writing-for-agents:81` 的 no-op 測試）。同時把路由句從「陳述關係」改成「陳述動作」（「機關或廠商自行撰寫用 X」），語氣與另兩份一致。

---

### 5-5 合計

| | 字元 | est. tokens |
| --- | --- | --- |
| 現況 | 996 | ~810 |
| 提案 | 649 | ~512 |
| 差 | **−347（−35%）** | **−298（−37%）** |

換算：以官方「~100 tokens per Skill」為基準，現況是 2.7 倍，提案後降到 1.7 倍。對 CJK skill 而言 1.7 倍是合理的落點。

**上線前必做**：第八節的 description tuning，用 should-trigger / should-not-trigger 兩組 prompt 實測命中率，確認沒有掉點再換上去。**沒有實測就不要換**——使用者的約束是「不失去命中率」，這是唯一能證明的方法。

---

## 六、軸四：開發期產物 vs 發佈期產物的分離

使用者的觀察：資源路徑、參考資料、出處記錄被寫在 skill 可讀範圍內，對已完成的 skill 是無用資訊，應該只留在開發項目裡，不該被帶走。

**先說結論：這個直覺是對的，但在本倉庫它主要是「發佈面與維護面」的問題，不是「上下文」的問題**——因為第 3 小節查證的結果是：沒被指向的檔案在執行期不花上下文。真正的成本是體積、維護重複、以及「帶走 skill 的人拿到一堆看不懂也用不到的東西」。

### 6-1 本倉庫的實際稽核

**(a) 純開發期產物（建議搬出或刪除）**

| 項目 | 位置 | 字元 | est. tokens | 判定理由 |
| --- | --- | --- | --- | --- |
| 〈查證紀錄〉整節 | `skills/tw-gov-it-review/references/04-來源與查證.md:71-77` | 914 | ~636 | 維護者的查證 changelog。內容是「本次改了哪些檔案的哪一行」，甚至寫著「該誤植原在 `../tw-gov-it-docs/references/05-採購型態.md`」——這是 commit message，不是審查者需要的知識 |
| 〈為什麼需要這一份〉＋識別字串挑法原理 | `04-來源與查證.md:5-7`、`20-31`、`49-52` | ~1,030 | ~700 | 解釋 `check_sources.py` 為什麼要比大小而不是找字串、投標須知範本落後三年的故事。這是**寫這支腳本的人**需要的知識，執行期只需要「跑腳本；出現 `[異動]` 就不要引用該版本號」 |
| 〈依據等級〉 | `skills/tw-gov-it-docs/references/07-機關端工作說明書.md:9-11` | ~180 | ~130 | 逐節標示哪些是查證過的、哪些引自《政府機關資訊通報》第 325 期。**但第 12 行「各節…為依通用實務自行撰寫，非官方規範文字」要留**——那句改變 agent 行為（不得宣稱為官方規範） |
| 查證日期戳 | `07-機關端工作說明書.md:16`、`03-法規速查.md:19` 等處的「已查證…仍為現行版本」「（查證日期：115 年 8 月 12 日）」 | 散落 ~300 | ~200 | 查證動作的紀錄。**但「該檔所依據的是投標須知範本 112.6.30 版，而該範本已於 115.7.27 改版」這類是 runtime 知識要留**——它改變審查結論 |
| `STANDALONE.md` × 3 | `skills/*/STANDALONE.md` | 116,689 | 0（見 6-3） | 另一個發佈通道的建置產物，放在 Claude Code skill 目錄裡 |

**小計：約 2,400 字元、約 1,670 est. tokens 的真正開發期文字**（不含 STANDALONE）。誠實地說：**這比體感小**。原因見下。

**(b) 看起來像但其實不是（不要動）**

掃描全部 `SKILL.md`／`references/`／`assets/` 的「依據／出處／資料來源／備註／參考資料」共 44 處，**逐條看過後絕大多數是領域內容不是撰寫出處**：

- 「依據」在政府文書裡是法律用語。`references/05-採購型態.md:37`「政府資訊服務採購作業指引，是現行辦理資訊服務採購的主要依據」是要寫進交付文件的內容。
- `references/03-範例集.md:33` 的「需求說明書出處」是需求追溯表的**欄位名稱**。
- `references/02-交付文件規格.md:63` 的「參考資料」是 SRS 章節規格裡的一個章節名。

**所以不能用關鍵字掃描做批次刪除**，必須逐條問：「這句話改變的是 agent 產出的內容（留），還是記錄了作者當初怎麼查到的（刪）？」

**(c) 孤兒檔案稽核**

逐一比對每個 `SKILL.md` 指向的路徑：

| skill | references | assets | scripts | 結果 |
| --- | --- | --- | --- | --- |
| `tw-gov-it-docs` | 01–07 全部被 `SKILL.md:33-43` 指到 | 00–13 全部被 `SKILL.md:51-66` 指到 | `check_layout.py` 在 `SKILL.md:68`；`make_docx_skeleton.py` 在 `references/06-Word範本.md:116` | **無孤兒**（`make_docx_skeleton.py` 是一層引用，符合規範） |
| `tw-gov-it-review` | 01–04 全部被 `SKILL.md:23,32,39,49` 指到 | 無 | 兩支都在 `SKILL.md:29,46` | **無孤兒** |
| `tw-gov-ta-docs` | 01 被 `SKILL.md:9,15,38` 指到 | 兩份都在 `SKILL.md:9-11,23` | 兩支都在 `SKILL.md:24-25` | **無孤兒** |

**唯一的孤兒是 `STANDALONE.md` × 3。** 沒有任何 `SKILL.md` 提到它。這是好事（不會被誤讀），也是它該搬走的理由（它不屬於這個包）。

### 6-2 官方規範怎麼說（查證結果：**基本上沒說**）

- **Agent Skills spec 明確允許任何檔案**：
  > "A skill directory may contain any files and directories beyond the required `SKILL.md`. The conventions below are recommendations for organizing common types of content."
  > — [agentskills.io Specification §Optional directories](https://agentskills.io/specification)

  spec 只定義了 `scripts/` / `references/` / `assets/` 三個慣例目錄，**沒有任何「開發期 vs 發佈期」的區分，也沒有 `.skillignore` 之類的排除機制**。

- **但 Anthropic 自己的打包腳本有硬編碼的排除清單**，而且其中一項正是開發期產物：
  ```python
  EXCLUDE_DIRS = {"__pycache__", "node_modules"}
  EXCLUDE_GLOBS = {"*.pyc"}
  EXCLUDE_FILES = {".DS_Store"}
  # Directories excluded only at the skill root (not when nested deeper).
  ROOT_EXCLUDE_DIRS = {"evals"}
  ```
  — [anthropics/skills `skills/skill-creator/scripts/package_skill.py`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/package_skill.py)

  `evals/`（測試案例、grading.json、benchmark.json）**住在 skill 目錄裡，但打包時被剝掉**。這是官方唯一一個「開發期材料放在 skill 目錄但不進發佈包」的具體先例。機制是**打包腳本的硬編碼清單，不是使用者可設定的 ignore 檔**。

- **`anthropics/skills` repo 自己怎麼放 provenance？** 逐一列出 `skills/docx`、`skills/pdf`、`skills/xlsx` 的完整檔案樹（見下），結果是：**skill 目錄裡只有執行期材料**——`SKILL.md`、`LICENSE.txt`、被 `SKILL.md` 指到的 `.md`、`scripts/`、以及腳本要吃的 `.xsd` schema。**沒有 CHANGELOG、沒有來源清單、沒有研究筆記、沒有版本沿革。**

  provenance 性質的東西全部在 **repo root**：`README.md`、`THIRD_PARTY_NOTICES.md`、`spec/agent-skills-spec.md`、`.claude-plugin/marketplace.json`。

  這是**觀察到的慣例，不是白紙黑字的規則**——官方沒有一句話說「不要把出處放進 skill 目錄」。但三個獨立範例一致，值得採信。

- **`metadata` frontmatter 欄位能不能裝 provenance？** 可以，但只能裝 string→string 的扁平 map：
  > "A map from string keys to string values. Clients can use this to store additional properties not defined by the Agent Skills spec"
  > — [agentskills.io Specification](https://agentskills.io/specification)

  Claude Code 補充："Claude Code doesn't act on its contents"（[Claude Code Skills §Frontmatter reference](https://code.claude.com/docs/en/skills)）。**注意：frontmatter 在 Level 1，理論上一直在上下文裡。** 沒有一手來源說明 `metadata` 是否也被送進 system prompt（官方只說 metadata 層是 `name` 與 `description`）。**不要把出處塞進 `metadata`**——省不了什麼，還可能反而變成常駐成本。列為未查證項。

### 6-3 沒被指向的檔案在執行期花上下文嗎？（**查證結果：不花，但可被翻到**）

這是使用者最關鍵的問題，逐條列出證據。

**證據 A：官方明說未被讀取的檔案成本為零。**
> "**No context penalty for large files:** Reference files, data, or documentation don't consume context tokens until actually read."
> "The rest stay on the filesystem and cost zero tokens."
> "There's no context penalty for bundled content that isn't used."
> — [Best practices §Runtime environment](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

**證據 B：官方明說發現途徑是 `SKILL.md`，不是自動的目錄樹。**
> "Reference supporting files from `SKILL.md` so Claude knows what each file contains and when to load it"
> — [Claude Code Skills §Add supporting files](https://code.claude.com/docs/en/skills)

> "Claude accesses these files only when referenced."
> — [Skills overview §Level 3](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

**證據 C：Claude Code 明列被注入的東西，其中沒有檔案樹。**
> "(default) | Yes | Yes | Description always in context, full skill loads when invoked"
> "the rendered `SKILL.md` content enters the conversation as a single message"
> — [Claude Code Skills](https://code.claude.com/docs/en/skills)

**證據 D：但 agent 有 filesystem 存取，會自己翻。**
> "Claude navigates your skill directory like a filesystem."
> "**Ignored content:** If Claude never accesses a bundled file, it might be unnecessary or poorly signaled in the main instructions."
> — [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

**判定**：答案是 **(a) 預設不讀，成本為零**，但帶一個 caveat——agent 手上有 bash 與 Read，若它決定 `ls` 一下 skill 目錄，就會看到 `STANDALONE.md` 這個 178 KB 的檔名，而且**它的名字聽起來像是「完整版」，有非零機率被誤開**。真開下去就是一次 52,800 est. tokens 的意外。

**所以修法是「移出目錄」而不只是「不要連結它」**——目前已經沒有連結它了，風險仍在。

同一份證據也回答了 `references/`／`assets/` 的問題：22 個檔的 74,400 est. tokens **不是常駐成本**，`SKILL.md` 的路由表寫得夠準，agent 就只會開需要的那一兩個。

**如何自行實測**（因為以上是文件推論，不是本機觀察）：

1. `/context` 看 Skills 那一列的數值，這是「listing 套上預算後模型實際收到的大小」（[Claude Code Skills](https://code.claude.com/docs/en/skills)）。刪掉 `STANDALONE.md` 前後各看一次——**數值應該完全不變**，這就證明它不在 listing 裡。
2. `/doctor` 取得 listing 的 context 成本估計與最大貢獻者（同一份文件明文說 `/doctor` 提供這個）。
3. 起一個乾淨 session，觸發 skill，跑完一個真實任務，然後檢查 transcript 裡有沒有出現對 `STANDALONE.md` 的 Read。跑 5～10 次估出誤開機率。

### 6-4 建議的分離機制（本倉庫的具體路徑）

原則：**skill 目錄 = 執行期材料；repo 其他地方 = 開發期材料。** 與 `anthropics/skills` 觀察到的慣例一致。

| 現在 | 建議搬到 | 說明 |
| --- | --- | --- |
| `skills/tw-gov-it-review/references/04-來源與查證.md` §查證紀錄（71-77 行） | `docs/provenance/查證紀錄.md` | 純 changelog。**這會牴觸 `CLAUDE.md`〈引用官方文件時〉現行的「查證後在該檔的『查證紀錄』加一列」，改的時候要同步改 `CLAUDE.md`，不要默默改掉** |
| `04-來源與查證.md` 的腳本原理段（5-7、20-31、49-52 行） | `docs/provenance/check_sources-設計.md`，或直接寫進 `scripts/check_sources.py` 的 docstring | 這是寫腳本的人的知識。留在 skill 裡的版本壓成三行：怎麼跑、`[異動]` 代表什麼、無網路怎麼辦 |
| `references/07-機關端工作說明書.md:9-11`〈依據等級〉 | `docs/provenance/07-依據對照.md` | 第 12 行留在原處 |
| `skills/*/STANDALONE.md` × 3 | `dist/STANDALONE/*.md`（repo 內、skill 目錄外） | 見下 |

**`STANDALONE.md` 的處理**（改 `tools/build_standalone.py`）：

目前輸出路徑在 `tools/build_standalone.py:80`：`out = skill_dir / "STANDALONE.md"`。建議改成 repo 根的 `dist/STANDALONE/{skill_name}.md`。

改動很小（`build()` 完全不用動，只改輸出路徑與 `--check` 的比對路徑），效益是：

- skill 目錄回到「只有執行期材料」，**帶走 skill 的人拿到的是 skill，不是 skill ＋ 一份它的複本**
- 發佈體積 −116 KB（距離 30 MB 上限還很遠，但這是原則問題）
- 誤開風險歸零
- **既有用途完全不受影響**——`STANDALONE.md` 的用途是「上傳到 ChatGPT Knowledge / Claude Project / Gemini Gems」（`tools/build_standalone.py:9`），使用者是從檔案總管挑檔上傳，`dist/STANDALONE/` 反而更好找
- CI（`.github/workflows/check-sources.yml`）與 `CLAUDE.md`〈交出去之前〉的指令不變，只有路徑要同步更新

**保留 traceability 的方式**：`docs/provenance/` 用檔名對應 skill 檔（`04-來源與查證.md` → `docs/provenance/tw-gov-it-review-04.md`），並在每一則紀錄裡寫明它管轄哪個檔的哪一節。作者要查「這條規則哪來的」時翻 `docs/provenance/`；使用者永遠不會看到。這正是 `writing-for-agents:25` 說的：把成本從 context load 移到 cognitive load，而**維護者本來就該付 cognitive load**。

**`scripts/check_sources.py` 的歸屬是一個待決策**：它是維護工具（CI 已經在跑）還是使用者工具？`tw-gov-it-review/SKILL.md:43-49` 明確要求審查者在有網路時跑它，所以目前是使用者工具，**不建議搬**。但如果實際上沒有使用者會跑它，它連同 `04-來源與查證.md` 的大半內容都該進 `tools/`。這一題需要使用者自己決定，不要替他決定。

---

## 七、如何量測（不要用猜的）

本研究的所有 token 數字都是**用公式估算的**（CJK×1.0 ＋ 非 CJK×0.28），不是量測值。要驗證改善，用下列任一種。

### 7-1 Token counting API（唯一的權威數字）

免費，有 RPM 限制。端點與範例逐字取自 [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting)：

```bash
curl https://api.anthropic.com/v1/messages/count_tokens \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-opus-5",
    "system": "You are a scientist",
    "messages": [{"role": "user", "content": "Hello, Claude"}]
  }'
```
回傳 `{ "input_tokens": 14 }`。

> "Token counting is **free to use** but subject to requests per minute rate limits based on your usage tier."

**兩個必讀的 caveat**：

1. **token 數依模型而異，差很多**：
   > "Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer. The same input text produces approximately 30 percent more tokens than on earlier models. […] Recount prompts against the model you plan to use rather than reusing counts measured against earlier models."
2. 回傳值是**估計值**："The token count is an **estimate**."

用法：把 description 或整份 `SKILL.md` 當成 `system` 或 `messages` 內容丟進去，改寫前後各測一次，取差值。**這是本研究裡每一個 est. 數字應該被取代掉的地方。**

### 7-2 Claude Code 內建

| 指令 | 給什麼 | 來源 |
| --- | --- | --- |
| `/context` | Skills 那一列＝listing 套上預算後模型實際收到的大小 | [Claude Code Skills](https://code.claude.com/docs/en/skills) |
| `/doctor` | listing 的 context 成本估計與**最大貢獻者** | 同上 |
| `claude --debug` | listing 超出預算時會寫警告到 debug log | 同上 |
| `claude plugin validate .claude/skills` | 找出 frontmatter 解析失敗的 `SKILL.md`（需 v2.1.233+） | 同上 |

**關於 `/skill-doctor`**：在 Claude Code 文件裡查不到這個指令。文件裡的是 `/doctor`（一個 bundled skill）。列為未查證。

### 7-3 命中率實測（description 壓縮的唯一驗收方式）

Anthropic 官方的 `skill-creator` plugin 有現成的 description tuning 迴圈：

```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install skill-creator@claude-plugins-official
```

然後對它說「evaluate my tw-gov-it-docs skill with skill-creator」。它做的事逐字如下：

> "**Description tuning**: generates should-trigger and should-not-trigger prompts, measures the hit rate, and proposes description edits when the skill activates on the wrong requests"
> — [Claude Code Skills §Run evals with skill-creator](https://code.claude.com/docs/en/skills)

底層是 [`skills/skill-creator/scripts/run_loop.py`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_loop.py)，機制逐字：

> "It splits the eval set into 60% train and 40% held-out test, evaluates the current description (running each query 3 times to get a reliable trigger rate), then calls Claude to propose improvements based on what failed. […] returns JSON with `best_description` — selected by test score rather than train score to avoid overfitting."

**這正好對上使用者的約束**：它會給出「壓縮前 vs 壓縮後」的 trigger rate 數字。用法建議：

1. 先寫 eval query——**三個 skill 的 should-trigger 與 should-not-trigger 要互相交叉**（給 review 的 query 應該是 docs 的 should-not-trigger），因為第五節指出兩者的 description 名詞高度重疊。
2. 現況 description 跑一輪，記下 baseline trigger rate。
3. 本研究的提案跑一輪。
4. 只有在**沒掉點**時才換上去；掉點就從第五節列的「刪了什麼」把對應項目一條一條加回，每加一條再測。

另有一個一般性的基線比較法（不裝 plugin 也能做）：
> "Collect a few realistic prompts, run each one in a fresh session with the skill available and again with it disabled, and compare the results. A fresh session matters because leftover context from authoring the skill will mask gaps in the written instructions."
> — [Claude Code Skills §Evaluate and iterate on a skill](https://code.claude.com/docs/en/skills)

### 7-4 實際跑過之後：7-3 的兩個陷阱與一個更大的問題

2026-08-31 依 7-3 實際量測本倉庫三個 skill，記錄如下，因為 7-3 的建議照做會得到全 0 的假結果。

**陷阱一：`skill-creator` 的 `run_eval.py` 在 Claude Code 2.1.251 上量不到東西。** 兩個各自獨立的缺陷：

1. 它把待測 description 寫成 `.claude/commands/<name>.md`，也就是**自訂 slash command**。實測確認該指令確實出現在 session 的指令清單裡（`slash_commands` 含該名稱、總數 58），但模型從不主動叫它——自訂 slash command 是**使用者觸發**的，不在模型的工具選擇範圍內。要量 skill 觸發，必須裝成真正的 `.claude/skills/<name>/SKILL.md`。
2. 它的判定只看**第一個** tool call，名稱不是 `Skill`／`Read` 就判為未觸發。這個模型即使在空目錄也會先跑一次 `Bash` 探路，於是每一個真正的觸發都被誤判成未觸發。判定要掃完整串流。

**陷阱二：一次只裝一個 skill 量不到誤路由。** 姊妹 skill 的 description 名詞重疊（第五節）造成的搶觸發，只有在三個同時在場時才看得到。

**更大的問題：run 層級漂移大於待測效應。** 同一組 query、同一份 description，跑兩次的正例平均觸發率可以差 0.34：

| 正例平均觸發率 | R1 | R2 | R3 | R4 |
| --- | --- | --- | --- | --- |
| `tw-gov-it-docs` | 0.83 | 0.83 | 0.92 | 0.71 |
| `tw-gov-it-review` | 0.88 | 0.58 | 0.38 | **0.54** |
| `tw-gov-ta-docs` | 0.75 | 0.75 | 0.67 | 0.58 |

R4 的 `tw-gov-it-review` description 與 R1 **逐字相同**，卻差了 0.34；而且 R4 三個 skill 同時下修，包含兩個 description 從頭到尾沒動過的。R1→R3 看起來像「review 單調下降」的訊號，其實是這個漂移。

實務結論：

- **每題 3 runs、門檻 0.5 的設計，解析不了 0.3 以下的差異。** 要比較兩版 description，把兩版**在同一批 job 裡交錯跑**（各建一個專案目錄，job 交替送出），讓漂移對兩版等量作用；連續跑完 A 再跑 B 的設計會把漂移算到 description 頭上。
- **負例比正例穩定得多。** 四次 run × 三個 skill × 12 個負例＝144 次觀測，誤觸發率全部 0.00。「壓縮有沒有造成誤路由」這個問題這套設計答得了，「有沒有掉命中率」答不了。

---

## 八、未查證 / 無法確認

逐條列出本研究**找不到一手來源**的事情。這些不要當成事實用。

1. **CJK 每字元的 token 數。** Anthropic 沒有公開任何語言別的 tokens-per-character 數字。本檔一律用 CJK×1.0＋非 CJK×0.28 估算，這是**慣用經驗值不是官方值**。所有標 est. 的數字都應該用 7-1 的 API 取代。已知的官方資訊只有「Claude 4.7 之後的 tokenizer 對同樣文字多產生約 30% token」。
2. **description 該用中文還是英文寫。** 官方只規定第三人稱與「include key terms」，**沒有任何語言偏好的陳述**。第五節主張維持中文是推論（使用者打中文），不是查證。
3. ~~**本研究對 tw-gov-it-review description 刪去文件名詞清單會「提升」路由精準度的推論。**~~ **已實測，且推論不成立。** 誤路由率本來就是 0.00（144 次負例觀測全對），沒有精準度可提升。至於刪去後命中率有沒有掉，7-4 顯示這套量測的 run 層級漂移大於待測效應，答不了。最後的處置是 `tw-gov-it-review` 維持原 description，`tw-gov-it-docs` 與 `tw-gov-ta-docs` 的壓縮版保留（兩者的新版在兩次獨立 run 都與 baseline 同分）。
4. **Markdown 粗體在 description 裡有沒有作用。** 找不到任何說法。刪除的理由只是「確定占字元、沒有證據有用」。
5. **`metadata` frontmatter 欄位是否進 system prompt。** 官方描述 Level 1 只提 `name` 與 `description`；Claude Code 只說「不會對它的內容做任何動作」。是否計入常駐成本未知。因此第六節建議**不要**把 provenance 塞進 `metadata`。
6. **`/skill-doctor`。** Claude Code 文件裡沒有這個指令，只有 `/doctor`。可能是舊名或別的產品面的東西。
7. **`claude plugin eval`。** 同樣查不到這個子命令。文件裡的 eval 路徑是 `skill-creator` plugin ＋ `run_loop.py` ＋ `evals/evals.json`。查得到的相關子命令只有 `claude plugin validate`。
8. **官方有沒有規則說「開發期材料不該進 skill 目錄」。** 沒有。spec 明說 "may contain any files and directories"。本研究引用的是 (a) `package_skill.py` 排除 `evals/` 的先例，與 (b) `anthropics/skills` 三個 skill 目錄的觀察慣例。**兩者都是慣例證據，不是規則。**
9. **agent 自發開啟未被指向檔案的機率。** 官方文件說會 navigate skill directory like a filesystem，但沒有量化。`STANDALONE.md` 的誤開風險是推論，用 6-3 的方法可以實測。
10. **`skillListingBudgetFraction` 與 `skillListingMaxDescChars` 的預設值。** settings-reference 頁面只回傳了索引列，沒取到詳細條目。已知的是預算＝context window 的 1%、每筆上限 1,536 字元（來自 skills 頁）。實際預設值請直接查 [settings reference](https://code.claude.com/docs/en/settings-reference)。

---

## 九、建議的執行順序

| 順序 | 動作 | 風險 | 效益 |
| --- | --- | --- | --- |
| 1 | 跑 `/context` 與 `/doctor` 記下 baseline | 無 | 之後所有改動才有對照 |
| 2 | 裝 `skill-creator`，寫三個 skill 的交叉 eval query，記下現況 trigger rate | 無 | 第 3 步的驗收條件 |
| 3 | 換上第五節的三份 description，重跑 eval；掉點就逐條加回 | 中（會改變觸發行為） | −347 字元、−298 est. tokens，**每個 session** |
| 4 | 改 `tools/build_standalone.py` 輸出到 `dist/STANDALONE/`，同步改 `CLAUDE.md` 與 CI | 低（純路徑） | skill 目錄乾淨，誤開風險歸零 |
| 5 | 搬〈查證紀錄〉與腳本原理段到 `docs/provenance/`，同步改 `CLAUDE.md`〈引用官方文件時〉 | 低 | −1,670 est. tokens 的發佈面重量 |
| 6 | 壓縮 `tw-gov-it-docs/SKILL.md` 的 `assets/` 表格（3-1） | 低 | 觸發時 −700 est. tokens |
| 7 | 三份「硬規矩」各壓到 2～3 行（4-1 做法 1） | 低 | 觸發時 −250～400 est. tokens |
| 8 | no-op 獵殺（3-2），逐句跑測試 | 中（要人判斷） | 觸發時 −400～600 est. tokens |
| 9 | 給 9 個超過 100 行的 reference 加目錄（3-4） | 無 | 防漏讀 |

**不要做的事**：不要用關鍵字批次刪「依據／出處／備註」（6-1(b) 說明了為什麼會誤刪領域內容）；不要為了共用把三個 skill 綁成依賴（違反 `tw-gov-ta-docs` description 對使用者的明文承諾）。

---

## 附錄：一手來源清單

- [Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) — 三層載入模型、frontmatter 限制、架構
- [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — 500 行、description 寫法、progressive disclosure patterns、runtime environment
- [Extend Claude with skills（Claude Code）](https://code.claude.com/docs/en/skills) — 完整 frontmatter 表、skill listing 預算與 1,536 字元上限、`/doctor`、`/context`、skill-creator evals
- [agentskills.io Specification](https://agentskills.io/specification) — Agent Skills spec 本體（`anthropics/skills` 的 `spec/agent-skills-spec.md` 只是指向這裡的三行指標）
- [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) — count_tokens 端點、免費、tokenizer 差異
- [Using Agent Skills with the API](https://platform.claude.com/docs/en/build-with-claude/skills-guide) — 30 MB 上限、單次 20 個 skill
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — metadata 於 startup 預載進 system prompt
- [Claude Code settings reference](https://code.claude.com/docs/en/settings-reference) — `skillListingBudgetFraction`、`skillListingMaxDescChars`
- [anthropics/skills](https://github.com/anthropics/skills) — 實際 `SKILL.md` 範例（`docx`、`pdf`、`xlsx`、`skill-creator`、`mcp-builder`、`brand-guidelines`）、`package_skill.py` 的排除清單、repo 的 provenance 放置慣例
- `CLAUDE.md` — 本倉庫的既有慣例
- 撰寫規範 `writing-for-agents`（含 `SKILL-MECHANICS.md`）與 `writing-great-skills` — 研究當時作者本機的 agent 文件撰寫規範，**不隨本倉庫散布**，路徑不列
