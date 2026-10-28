# SiteCraft 品質閘門（qa/）

品質標準以 Awwwards、Webby Awards、FWA 獲獎作品為目標。每次改 `templates/site/onepage.html.j2`
或 `build_site.py` 之後，重新產生網站並跑這個閘門；全部 PASS 才算完成。

```bash
cd sitecraft/qa
npm install && npx playwright install chromium      # 只需一次
python ../build_site.py --sample                       # 重新產生三個範例站
node qa.js                                             # 或 node qa.js demo-cafe,demo-hair,demo-pet 回合名稱
```

每個站點檢查：
- 桌機 1440×900、筆電 1366×768、手機 390×844 截圖（首屏、整頁、選單、深色模式）
- axe-core（WCAG 2.1 AA + best-practice）在桌機與手機、亮色與深色模式皆為 0 違規
- 無橫向溢出；所有可點元素至少 44px；整頁零 emoji；無 console / page error
- hero 區塊高度恰好等於示範橫幅以上的可視範圍（三種尺寸）
- 功能：首屏不顯示快速列、漢堡按鈕可開可關、選單是真正的對話框（焦點進入且困在裡面）、
  相簿上一張／下一張與計數器正確、服務列可用鍵盤聚焦、標題第二行無縮排、資訊列不截字
- 計算樣式：h1 真的套用展示字型（Fraunces / Syne）且與內文不同、網頁字型已載入、
  相簿磚比例 4:3 與 3:4、有 og:image
- Lighthouse 行動版：效能、無障礙、最佳做法、SEO 都要 90 以上

輸出：`qa/shots/<回合>/` 內有截圖與 `report.json`。
接著把截圖交給一位「不知道你結論」的評審，用六項指標（視覺、創意、內容層級、易用性、互動、工藝）
各打 1～10 分；每項 8 以上且平均 8.5 以上才算達標，否則依修正清單再做一輪。
