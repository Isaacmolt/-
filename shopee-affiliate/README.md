# 蝦皮分潤（Shopee Affiliate）— 第二條收入線

SheetCraft AI 的第二個事業線：用「小資效率實驗室」這個中文帳號，在 Threads / IG 推蝦皮好物賺分潤，同時導購自家 Google Sheets 模板。

## 先看這些

| 順序 | 檔案 | 內容 |
|------|------|------|
| 0 | [`起床看這裡-蝦皮分潤.md`](起床看這裡-蝦皮分潤.md) | 今天要做的事，照做就好 |
| 1 | [`01-制度懶人包.md`](01-制度懶人包.md) | 2026 年規則：分潤比例、7 天歸因、分級、提領、禁止事項 |
| 2 | [`02-策略與90天路線圖.md`](02-策略與90天路線圖.md) | 定位、賽道、目標、90 天計畫、風險 |
| 3 | [`03-利基發想.md`](03-利基發想.md) | 12 個方向評分、推薦組合、20 個貼文點子、選品清單 |
| 4 | [`04-內容SOP.md`](04-內容SOP.md) | 貼文公式、短影音腳本、揭露、每日流程、數據判讀 |
| 5 | [`05-請款稅務與合規.md`](05-請款稅務與合規.md) | 對帳、勞報單、5 萬門檻、公司戶、處罰 |

## 快速開始

不想打指令：Windows 雙擊 `一鍵執行-Windows.bat`、Mac 右鍵打開 `一鍵執行-Mac.command`，或到 GitHub **Actions → Shopee Affiliate → Run workflow**。詳見 `起床看這裡-蝦皮分潤.md` 的「工具怎麼打開」。

有終端機的話：

```bash
cp shopee-affiliate/config.example.json shopee-affiliate/config.json   # 填帳號名稱、揭露文字
# 編輯 shopee-affiliate/products.csv，把 12 個範例換成真實商品
make shopee-all
```

`make shopee-all` 會跑四支腳本：

| 指令 | 腳本 | 產出 |
|------|------|------|
| `make shopee-niches` | `scripts/shopee_niche_scorer.py` | `reports/niche-ranking.md` 利基排名 |
| `make shopee-links` | `scripts/shopee_link_builder.py` | `reports/link-batch.csv` 貼後台用的批次表、`linkpage/index.html` 好物清單頁 |
| `make shopee-posts` | `scripts/shopee_post_generator.py` | `posts/<ID>/*.txt` 貼文與腳本草稿、`posts/schedule.csv`、`reports/content-calendar.md` 30 天排程 |
| `make shopee-tracker` | `scripts/shopee_tracker.py` | `tracker.xlsx` 7 分頁營運追蹤表（可匯入 Google Sheets） |
| `make shopee-roi` | `scripts/shopee_roi_calc.py` | `reports/income-model.md` 收入模型 |

## 工作流程

```
products.csv（選品）
    │
    ├─ shopee_link_builder ──→ link-batch.csv ──→ 到後台逐一產生短連結 ──→ 填回 products.csv 的 affiliate_link
    │                                                                              │
    │                          ┌───────────────────────────────────────────────────┘
    │                          ▼
    ├─ shopee_link_builder ──→ linkpage/index.html（放 Threads / IG 個人檔案）
    │
    ├─ shopee_post_generator ─→ posts/ 草稿 + 30 天排程 ──→ 改口氣 ──→ 發文
    │
    └─ shopee_tracker ───────→ tracker.xlsx ──→ 每天填點擊/訂單 ──→ 每月對帳/提領
```

蝦皮分潤短連結只能從官方後台產生，沒有公開 API，所以「產生連結」這一步是手動的。批次表把網址和 sub_id 都排好了，一個商品大約 20 秒。

## 目錄

```
shopee-affiliate/
├── README.md                       ← 你在這
├── 起床看這裡-蝦皮分潤.md             ← 行動清單（含「工具怎麼打開」）
├── 一鍵執行-Windows.bat / 一鍵執行-Mac.command   ← 雙擊跑全部工具
├── 01-制度懶人包.md … 05-請款稅務與合規.md
├── niches.json                     ← 12 個利基方向與評分
├── products.csv                    ← 選品庫（12 個範例，請換成真實商品）
├── config.example.json             ← 帳號設定範本（複製成 config.json，已 gitignore）
├── templates/
│   ├── threads.md                  ← 5 種 Threads 貼文模板
│   ├── instagram.md                ← 輪播與 Reels 文案模板
│   └── shopee_video.md             ← 15 秒 / 30 秒短影音分鏡
├── posts/                          ← 產生的草稿與 schedule.csv
├── reports/                        ← 利基排名、批次表、收入模型、發文日曆
├── linkpage/index.html             ← 好物清單頁（GitHub Pages 部署）
└── tracker.xlsx                    ← 營運追蹤表
```

## sub_id 命名

`{平台}_{利基}_{年月}_{商品ID}`，例：`th_home_202610_p001`。後台報表可以用 sub_id 篩選，就能知道哪個平台、哪個利基、哪個月的哪篇文帶單。只能用英數底線，50 字內。
