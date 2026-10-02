#!/bin/bash
# 蝦皮分潤工具 — 一鍵執行（Mac）
# 第一次雙擊若被擋住：在檔案上按右鍵 → 打開 → 再按一次「打開」。
cd "$(dirname "$0")/.." || exit 1
echo "=========================================="
echo " 蝦皮分潤工具 - 一鍵執行"
echo "=========================================="
echo
if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] 找不到 Python。請到 https://www.python.org/downloads/ 下載安裝後再雙擊這個檔案。"
  read -r -p "按 Enter 關閉 "
  exit 1
fi
echo "[1/6] 安裝需要的套件 openpyxl ..."
python3 -m pip install -q openpyxl
echo "[2/6] 利基排名 ..."
python3 scripts/shopee_niche_scorer.py
echo "[3/6] 連結批次表 + 好物清單頁 ..."
python3 scripts/shopee_link_builder.py
echo "[4/6] 貼文草稿 + 30 天排程 ..."
python3 scripts/shopee_post_generator.py
echo "[5/6] 營運追蹤表 tracker.xlsx ..."
python3 scripts/shopee_tracker.py
echo "[6/6] 收入模型 ..."
python3 scripts/shopee_roi_calc.py
echo
echo "=========================================="
echo " 完成！產出都在 shopee-affiliate/ 資料夾："
echo "   tracker.xlsx          營運追蹤表（會自動打開）"
echo "   posts/                貼文草稿、schedule.csv"
echo "   reports/              利基排名、批次表、發文日曆、收入模型"
echo "   linkpage/index.html   好物清單頁（雙擊可預覽）"
echo "=========================================="
open shopee-affiliate/tracker.xlsx 2>/dev/null || true
echo
read -r -p "按 Enter 關閉 "
