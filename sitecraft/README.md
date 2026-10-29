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

品質標準以 Awwwards、Webby Awards、FWA 獲獎作品為目標，每次改模板都跑一輪自我檢查：
`axe-core` 無障礙 0 違規（亮／暗色）、Lighthouse 行動版四項 90 以上、無橫向溢出、所有可點元素 44px 以上、
首屏在 1366×768 / 1440×900 / 390×844 都放得進一屏、選單可關可困焦點、相簿可翻、鍵盤可達、無 JS 也可讀、
減少動態偏好生效、焦點框對比足夠、中文不孤字、整站零 emoji（工具在 `qa/`，見 `qa/README.md`），
再交給獨立評審依六項指標打分、修到過關。

每個網站都有：
- 三種字型語氣 × 兩種首屏構圖，16 個類別分散配置，避免看起來像同一頁換色：編輯感（Fraunces + Noto Serif TC）、粗獷感（Syne + Noto Sans TC 900）、清爽感（Space Grotesk + Noto Sans TC 600）；圖騰在右（side）或圖騰橫幅居中（band），由 `themes.json` 的 `mode` 與 `hero` 決定
- 字型自架：建站時用 fontTools 依該頁實際用到的字，從開源變數字型切出 3～4 個 woff2（標題子集約 30 KB、內文約 110 KB、英文約 40 KB），放在 `sites/<slug>/fonts/`，首屏標題字型 preload；不再連 Google Fonts，手機上少掉上百個字型子集造成的反覆重排。原始字型第一次會下載到 `sitecraft/.fonts/`（不進 git）；沒裝 fonttools 或離線時加 `--google-fonts` 退回 Google Fonts 連結
- 全屏 hero：逐字進場的店名、該類別專屬的線條圖騰（咖啡杯、剪刀、貓掌、牙科十字等 17 種，在 `data/motifs.json`）會跟著游標產生視差、單一主要行動（LINE 為主、電話其次、地圖為文字連結）
- 首屏資訊列：今日營業（即時判斷營業中／休息中／今日公休與下次開門時間）、Google 評分與評論數、地址、電話
- 跑馬燈帶資訊：類別、區域、評分、今日時段、服務名稱
- 關於我們：以介紹的第一句當大標、三大特色編號清單
- 服務列：四項可點的連結，直接開 LINE 並預填「想詢問：某服務」；在 `content.json` 的 `services[].price` 填價格（例如 `NT$150 起`）就會多一欄價目
- 店的樣子／店內環境：可拖曳、可按鍵的橫向捲動，最後一張也能對齊；有照片時點照片開燈箱（原生 dialog，置中，方向鍵翻頁、Esc 關閉）。沒有照片時不假裝：一張標語直排（依標點分欄）加三張線條示意圖（場景、織紋、雙色拼接），並註明「正式上線時會換成店內實拍照片」。照片放 `sites/<slug>/img/`，`content.json` 的 `gallery` 只要寫檔名
- 首屏插畫：17 個類別都有完整的場景插畫（`motifs.json` 的 `hero`：兩種線寬、強調色實心、指定幾筆做閒置微動）；側邊版型放在右側，置中版型放在一排靜物的中間，手機放在按鈕下方的獨立區塊，不會壓到按鈕；結尾與選單各用不同的圖。品質閘門會檢查每個類別都有場景、每個強調色在深色底上都看得清楚
- 沒有照片時，關於我們右欄放一張類別圖騰插畫；有照片時換成第二張照片
- 版型依字型語氣變化：編輯感（襯線）的關於我們是左文右圖、服務是菜單帳本；清爽感的關於我們是大標配一張出血到邊緣的插畫、服務是卡片；粗獷感的服務是深色菜單板、價格放大
- 每一區的線條圖（區塊標題旁的小圖、關於我們的插畫、招牌卡、相簿示意圖）在捲到時才一筆一筆畫出來；結尾的蒸氣只在營業中出現
- 首屏店名只在詞與詞之間換行（「小巷裡的／老宅／髮型／設計／工作室」），不會把一個詞拆成兩行；首屏營業狀態顯示「這一段」的時間（例如營業中 14:00 打烊、休息中 17:00 開門），午晚兩段、營業到凌晨都正確
- 有照片時：第一張進首屏（桌機是右側拱門框、手機是整片背景加漸層），第二張放在關於我們；相簿磚依照片實際長寬決定直式或橫式，燈箱完整顯示照片（不裁切）、可左右滑
- 每個類別的服務標題、相簿標題與招牌區塊不同（`themes.json` 的 `services_title`、`gallery_title`、`signature`）：餐飲類把第一項做成「今日推薦」大卡，服務類是「一二三」三個步驟；`content.json` 可以覆寫
- 分享預覽圖（og.png）用網站同一套字型與類別插畫（需要 cairosvg；沒有就只畫強調色圓）
- 營業狀態一律用台北時間判斷；手機上的快速聯絡鈕在服務與營業資訊區自動讓開，示範橫幅捲動後縮成一行
- 關於我們的大標每個類別一句（`themes.json` 的 `statement`，Claude 文案也會產生），不再用「店名位於某區」的公式句；文案與 content.json 一律不放 emoji，舊檔案重建時會自動清掉
- 營業資訊：一週時段（標今天）、一鍵複製地址、電話、LINE、Google 地圖嵌入
- 收尾區：大字電話 + LINE；頁尾社群連結與製作者署名
- 手機：全螢幕選單（含撥打／LINE／導航）、底部「電話｜LINE」快速列；深色模式、減少動態偏好、鍵盤焦點樣式、略過連結
- SEO：`LocalBusiness` 結構化資料（含營業時間與評分）、OG 標籤、canonical。單一 HTML 檔、無框架、無後端。

## 改東西

| 想改 | 去哪裡 |
|---|---|
| 價格、品牌名、加購、縣市與類型 | `config.json` |
| 某一類店的顏色 / 字型語氣 / 預設文案 | `data/themes.json`；線條圖騰在 `data/motifs.json` |
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
