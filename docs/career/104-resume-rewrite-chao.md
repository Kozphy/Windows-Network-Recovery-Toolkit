# 104 履歷改寫稿（趙晟佑）

依目前 PDF 匯出內容改寫。目標：用 **會計／內控背景 + WNRT 技術風險證據平台** 對準  
`Finance Transformation` / `Enterprise Technology & Performance` / 科技風險相關職缺。  
**不要**再把「會計師事務所新人」當唯一故事；也**不要**讓直播／量化交易蓋過主軸。

使用方式：到 104「修改履歷」依區塊貼上；自傳可縮成一欄。

---

## 0. 先改這 5 個開關（最重要）

| 欄位 | 現況問題 | 建議改成 |
|------|----------|----------|
| 希望職稱 | 還行，但職類對不上 | 保留 1 主 + 1 備：`Technology Risk / Control Analytics` 或 `Finance Transformation Analyst`；備選 `資料分析師（財務／內控）` |
| 希望職類 | 會計師、記帳士為主 | 改偏：`系統分析師`、`軟體工程師`、`財務分析`、`風險管理`、`顧問`（拿掉純記帳／出納當第一志願） |
| 希望產業 | 太散 | 優先：`軟體及網路`、`顧問`、`金融相關`；會計服務業可留但不要唯一 |
| 自傳結尾 | 「希望從會計師事務所基礎職開始」 | 改成「財務／科技風險、內控數位化、證據與治理」 |
| 工作經驗排序 | 直播主在最上面 | **直播改「其他／兼職」或刪簡**；主軸改 WNRT + 接案系統 + 實習 |

---

## 1. 履歷抬頭（104 顯示名下一行）

**建議顯示：**

> 趙晟佑｜會計背景 × 技術風險／控制分析  
> Windows endpoint 證據管線、policy-gated remediation、hash-chained audit（WNRT 開源）  
> 台中｜可遠端｜希望：Finance Transformation / Tech Risk & Control Analytics

英文姓名建議用 **Chao, Cheng-Yu**（或你護照拼音）；`Zixsa` 可留社群，但 104／人資欄位用正式拼音。

---

## 2. 個人簡介（取代現有長自我介紹）

可貼 104「自我介紹」：

```text
會計系畢業，具會計師事務所與國稅局實習經驗，熟悉 working paper、資料驗證、內控與合規導向流程。

近年以開源專案 Windows Network Recovery Toolkit（WNRT）實作「技術風險與控制分析」方向：
針對 Windows 端點常見的死 localhost proxy／WinINET 漂移等可靠性問題，建立
可重現取證 → 分級分類（含 limitations）→ 控制測試 → 預設 dry-run 的 remediation 預覽
→ hash-chained 審計 custody（domain event kernel）的證據管線。

定位不是防毒／EDR，而是可審計、可回放的 evidence & governance 工具鏈。
擅長把「看起來 online 但其實壞掉」的端點問題，轉成可解釋的分類、政策門檻與稽核軌跡。

技術：Python、CLI／FastAPI、fixture 測試、Git、Docker 基礎；文件與治理表述清楚。
作品：https://github.com/Kozphy/Windows-Network-Recovery-Toolkit
```

（字數可再壓到 104 上限；重點是 **WNRT 進第一段**。）

---

## 3. 專案成就（104「專案」一定要加這塊）

**專案名稱：** Windows Network Recovery Toolkit（Technology Risk & Control Analytics）

**期間：** 2024／2025～進行中（依你真實開始時間填）

**說明（可貼）：**

```text
• 設計並實作 Windows 端點代理／連線可靠性之證據收集與分類管線（fixture-first、可回放）。
• 建立 Observation → Classification → Policy → Remediation preview → Audit 分層，
  預設 dry-run；高風險變更需 typed confirmation；預設阻擋 process kill／防火牆重置等。
• 實作 Level-1 domain event kernel（wnrt.domain_event.v1）：統一 audit／decision／guardian
  寫入與 verify；支援 hash chain + tip；篡改可被檢測。
• 產出治理導向輸出（limitations[]、governance report／Power BI 匯出路徑）與安全契約測試。
• GitHub：https://github.com/Kozphy/Windows-Network-Recovery-Toolkit
```

把舊的「交易軟體研究與測試」降為次要專案或刪短。

---

## 4. 工作經驗怎麼排

### A. 自營／Freelance（保留，但改標題與前 4 點）

**職稱建議：** 獨立開發者（技術風險工具／自動化系統）  
**不要**只寫「量化交易系統開發者」當唯一身份。

精簡版 bullet（104 每段 4–6 點即可）：

```text
• 以 Python 開發自動化與資料管線；近年聚焦 Windows 端點可靠性取證與治理工具（WNRT）。
• 具備事件驅動架構、API 整合、回測／風險指標與 Docker／Linux 部署經驗。
• 強調可重現實驗、風險限制（部位／停損規則）與文件化流程。
• （可選 1 行）早期亦從事加密市場策略研究與交易所 API 整合——作為資料／自動化背景，非求職主軸。
```

加密交易細節留 2 點即可，避免整頁 Binance／Sharpe。

### B. 資展國際學員（保留）

維持 C#／MSSQL／驗證／安全；加一行：

```text
• 理解企業 Web 系統與資料庫在「資料完整性／驗證」上的基本控制思維。
```

### C. 國稅局／會計師事務所實習（保留，這是差異化）

強調：**文件完整性、差異辨識、內控 SOP、working paper**——這正好接到 WNRT 的 limitations／audit。

### D. 直播主

- 投 Finance／Tech Risk：**刪除或收到「其他經歷」一行**（內容經營／數據觀察）。  
- 放在最上方會嚴重稀釋專業訊號。

---

## 5. 專長／技能標籤（大掃除）

**保留／置頂：**  
`Python` `Git` `SQL` `Docker` `Linux` `Excel` `內控／審計文件` `資料驗證` `自動化` `FastAPI`（若屬實）

**拿掉或藏很後面：**  
直播造型、Premiere、短影音、一排 TQC 輸入（可留 Excel／PPT 各一）、雜亂 `#ReactJS`（非主軸就別搶戲）

**證照：** TOEIC 605、會計丙級可留；TQC 輸入類不必佔版面。

---

## 6. 自傳（104 自傳欄）— 四分之一長度即可

```text
會計訓練讓我習慣「證據、勾稽、文件紀律與內控邊界」。實習時接觸 working paper 與稅務文件檢核，
理解合規流程如何要求可追溯性。

我用開源專案 WNRT 把同樣思維做到技術風險場景：端點異常先取證與分級，而不是直接「修一修」；
remediation 預設預覽，審計資料可驗證。這與財務轉型／科技風險顧問需要的
「可解釋、可稽核、可落地」一致。

職涯上希望加入需要「會計／風險語言 + 工程落地」的團隊，例如財務轉型、科技風險、
內控數位化或平台可靠性相關角色，持續把控制思維做成可用系統。
```

刪掉「從會計師事務所基礎職開始」那段，除非你真的只投事務所。

英文自傳若要留，改成同一故事（WNRT + controls），不要只重複會計實習。

---

## 7. 求職條件建議

```text
希望性質：全職
希望待遇：面議（或給合理區間，避免「依公司規定」過弱）
希望地點：台中市；可接受遠端／混合
希望職稱：Finance Transformation Analyst／Technology Risk & Control Analytics
工作內容關鍵字：資料驗證、內控、異常分析、Python、系統化流程、稽核軌跡、報表／治理輸出
```

---

## 8. 投 104 時的配對邏輯

| 職缺關鍵字 | 你履歷要亮的句 |
|------------|----------------|
| 內控、SOX、審計數位化 | 實習 working paper + WNRT limitations／audit verify |
| 財務轉型、ERP、流程優化 | 會計背景 + 自動化／資料管線 + 治理輸出 |
| 軟體工程、SRE、平台 | WNRT CLI、測試、domain event、dry-run safety |
| 純記帳、出納 | **先別投**或另做一版「會計助理履歷」（不要用 WNRT 版硬投） |

一職缺一微調：標題句換 1 行即可，不必做十版。

---

## 9. 改完自我檢查（10 分鐘）

- [ ] 第一屏看得到 WNRT 或「技術風險／控制分析」  
- [ ] 直播不在工作經驗最上面  
- [ ] 自傳不再寫「只想進事務所打雜起薪」  
- [ ] 量化交易不是最長的一段  
- [ ] GitHub 連結可點、README 30 秒能懂  
- [ ] 職類與職稱一致  

---

## 10. 和「就業班」的關係

這版履歷的校準是：**會計可信度 + WNRT 辨識度**。  
不需要再報全端就業班來「填履歷」；若 104 職缺要雲端部署證明，再補 **一個** Docker／簡易 API 部署連結即可。
