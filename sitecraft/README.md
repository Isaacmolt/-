# SiteCraft — 在地商家一頁式官網代工（起床操作指南）

> 一句話：**找 Google 地圖上還沒有官網的店家 → 先免費幫他做好網站草稿 → 寄信給老闆看 → 喜歡就付 NT$860 正式上線。**
>
> 和 Webild 那類「描述一下就生成網站」的工具一樣的產出，但我們把它做成可以批次跑、而且後面接著「找客戶 → 寄信 → 收款 → 交付」的完整流程。

## 四支腳本 = 四個步驟

| 步驟 | 指令 | 做什麼 |
|---|---|---|
| 1 找商家 | `python sitecraft/find_leads.py --city 台中市 --district 西區 --type 咖啡廳` | 用官方 Google Places API 搜店家，挑出**沒有官網**（或只有 FB / IG / LINE）的，存進 `data/leads.csv` |
| 2 做網站 | `python sitecraft/build_site.py` | 每家店產生一個 `sites/<slug>/index.html` 示範網站（有示範橫幅），推上 GitHub 就上線 |
| 3 寄信 | `python sitecraft/send_outreach.py --stage first --send` | 合併列印寄第一封信；4 天後 `--stage followup1`、再 5 天 `--stage followup2` |
| 4 管名單 | `python sitecraft/crm.py due` | 今天該做什麼：補 email、該追蹤誰、誰付款了、誰該上線 |

成交後：`crm.py won <slug>` → 老闆寄照片 → 放進 `sites/<slug>/img/`、改 `content.json` → `crm.py publish <slug>` → push → 示範橫幅消失、同一個網址變正式版。

## 第一次設定（約 20 分鐘，只做一次）

```bash
pip install -r sitecraft/requirements.txt
cp .env.example .env          # 已經有 .env 就把下面幾行加進去
```

### 1. Google Maps 金鑰（找商家用）
1. 到 <https://console.cloud.google.com/> 建專案 → 「API 和服務」→「程式庫」→ 搜尋 **Places API (New)** → 啟用（注意是 New，不是舊版）
2. 「憑證」→ 建立 API 金鑰 → 貼到 `.env` 的 `GOOGLE_MAPS_API_KEY`
3. 需要綁信用卡才能用，但我們用的 Text Search Enterprise SKU 每月約 1,000 次免費請求（一次最多 20 家店），正常使用不會收費。可在「配額」頁設每日上限保險。
4. 跑 `python sitecraft/find_leads.py --city 台中市 --type 咖啡廳 --district 西區 --dry-run` 看會查哪些關鍵字；拿掉 `--dry-run` 真的查。

### 2. Gmail 寄信（寄信用）
1. Google 帳號 → 安全性 → 開啟**兩步驟驗證**
2. 搜尋「應用程式密碼」→ 建立一組（16 碼）→ 貼到 `.env` 的 `SMTP_PASS`
3. `SMTP_USER` / `SENDER_EMAIL` 填你的 Gmail，`SENDER_NAME` 填對外名稱（預設 SiteCraft 小站工作室），`SENDER_PERSON` 填你的名字，`CONTACT_LINE` 填 LINE ID 或 lin.ee 連結
4. 測試：`python sitecraft/send_outreach.py --test 你自己的@gmail.com`
5. 建議另開一個專用 Gmail 寄冷信，不要用主帳號。

### 3. Claude 文案（選用）
`.env` 加 `ANTHROPIC_API_KEY`，`build_site.py --ai-copy` 就會幫每家店寫專屬標語、介紹和服務說明（每站約 NT$0.3）。沒有金鑰就用 `data/themes.json` 裡的主題預設文案，也已經很能看。

### 4. 示範網址
`config.json` 的 `demo_base_url` 預設是這個 repo 的 GitHub Pages：`https://isaacmolt.github.io/-/sites`。
`sitecraft/sites/` 推上 GitHub 後，`.github/workflows/deploy-pages.yml` 會把它部署到 `/sites/<slug>/`。
想要更好看的網址（例如 `sitecraft.tw/sites/xxx`）：買一個網域、在 repo Settings → Pages 設 custom domain，再改 `demo_base_url`。

## 每天的例行（約 1 小時）

```bash
python sitecraft/crm.py due                      # 1. 看今天待辦
#   → 缺 email 的：去 FB 粉專「關於」/ IG 簡介找，找到就 crm.py email <slug> <email>
python sitecraft/send_outreach.py --stage first  # 2. 預覽（存到 outbox/ 用郵件程式打開看）
python sitecraft/send_outreach.py --stage first --send --limit 25
python sitecraft/send_outreach.py --stage followup1 --send
python sitecraft/send_outreach.py --stage followup2 --send
#   有人回信 → crm.py replied <slug> --note "..."，24 小時內回
#   有人付款 → crm.py won <slug>，然後 send_outreach.py --stage after_payment --slug <slug> --send
python sitecraft/find_leads.py --city 台中市 --district 北區 --type 美髮沙龍   # 3. 補新名單
python sitecraft/build_site.py                   # 4. 幫新名單做網站
git add sitecraft/sites && git commit -m "sites: new demos" && git push
python sitecraft/crm.py stats                    # 5. 看漏斗
```

細節（定價、話術、找 email 的方法、法律注意事項）都在 **[PLAYBOOK.md](PLAYBOOK.md)**。

## 檔案地圖

```
sitecraft/
├── README.md              ← 你現在看的
├── PLAYBOOK.md            ← 業務 SOP：定價、話術、找 email、法律
├── config.json            ← 品牌、價格、加購、要掃的縣市/行政區/類型、寄信節奏
├── common.py              ← 共用工具
├── find_leads.py          ← 1. Google Places API 找沒官網的店
├── build_site.py          ← 2. 產生一頁式網站（示範版/正式版）+ 作品集頁
├── send_outreach.py       ← 3. SMTP 合併列印、預覽、每日上限、退訂
├── crm.py                 ← 4. 名單狀態、待辦、成交、上線、打包
├── data/
│   ├── themes.json        ← 16 種店家類型的配色、圖示、預設文案（可改）
│   ├── leads.sample.csv   ← 3 家虛構範例店（demo-cafe / demo-hair / demo-pet）
│   ├── leads.csv          ← 真實名單（.gitignore，不會上傳）
│   └── sent_log.csv       ← 寄信紀錄（.gitignore）
├── templates/
│   ├── site/onepage.html.j2   ← 網站模板（單檔、內嵌 CSS、含 JSON-LD、營業中判斷）
│   ├── site/index.html.j2     ← 作品集頁模板
│   └── email/01~05_*.txt      ← 五封信：首封、追蹤、最後、付款後、上線通知
├── sites/                 ← 產生的網站，每店一資料夾（index.html + content.json + img/）→ 部署到 Pages
├── outbox/                ← 預覽信 .eml（.gitignore）
└── deliveries/            ← crm.py package 打包的 zip（.gitignore）
```

## 網站長什麼樣

範例（推上去後）：
- 咖啡廳 <https://isaacmolt.github.io/-/sites/demo-cafe/>
- 美髮沙龍 <https://isaacmolt.github.io/-/sites/demo-hair/>
- 寵物美容 <https://isaacmolt.github.io/-/sites/demo-pet/>
- 作品集 <https://isaacmolt.github.io/-/sites/>

每個網站都有：手機優先的 RWD、店名/標語/類別、Google 評分徽章（連回地圖）、一鍵撥號 / LINE / 導航、關於我們 + 三大特色、四項服務卡片、相簿（示範版用示意圖，正式版放老闆的照片）、每週營業時間（自動標今天、判斷營業中/休息中）、Google 地圖嵌入、Facebook/IG/LINE 連結、SEO 用的 `LocalBusiness` 結構化資料、OG 標籤。單一 HTML 檔，沒有任何框架或後端，100 年後也能開。

## 改東西

| 想改 | 去哪裡 |
|---|---|
| 價格、品牌名、加購、縣市與類型 | `config.json` |
| 某一類店的顏色 / 圖示 / 預設文案 | `data/themes.json` |
| 某一家店的文字、聯絡方式、照片 | `sites/<slug>/content.json`，改完 `build_site.py --slug <slug> --rebuild` |
| 網站版型 | `templates/site/onepage.html.j2`，改完 `build_site.py --rebuild` 全部重做 |
| 信件內容 | `templates/email/*.txt`（第一行是主旨，支援 `{{ 變數 }}`） |
| 追蹤天數、每日上限 | `config.json` → `outreach` |

## 常見問題

**Google 地圖沒有店家 email，怎麼寄？**
對，Places API 不提供 email。`find_leads.py` 會抓到電話、地址、網站欄位（通常是 FB 粉專），email 要自己補：看 PLAYBOOK「找 email 的 7 個地方」。找不到就改走 LINE / 電話 / 直接到店，示範網站的網址一樣好用。

**可以用 Google 地圖上的店家照片嗎？**
不行，Google 的照片與評論文字有授權限制，不能拿來放在別人的網站上。示範版用示意圖，正式版請老闆提供照片（這也是我們「請提供照片」這一步的用意）。評分數字 + 連回 Google 地圖是 OK 的。

**一天可以寄幾封？**
程式預設 30 封/天、每封間隔 1～2.5 分鐘。Gmail 個人帳號技術上限 500/天，但冷信超過 50/天很容易被標成垃圾信。寧願少寄、每封都認真。

**老闆說不要再寄？**
`send_outreach.py --opt-out 他的@email` 或 `crm.py optout <slug>`，之後程式永遠不會再寄給他。這是法律和信譽的底線。

**名單會不會不小心 push 上 GitHub？**
`data/leads.csv`、`sent_log.csv`、`outbox/`、`deliveries/` 都在 `.gitignore`。`sites/` 會上傳（那是要公開的網站）。記得自己備份 `leads.csv`。
