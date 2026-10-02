@echo off
chcp 65001 >nul
title 蝦皮分潤工具
cd /d "%~dp0\.."
echo ==========================================
echo  蝦皮分潤工具 - 一鍵執行
echo ==========================================
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo [!] 找不到 Python。
  echo     請到 https://www.python.org/downloads/ 下載安裝，
  echo     安裝時記得勾選 "Add Python to PATH"，裝好後再雙擊這個檔案。
  echo.
  pause
  exit /b 1
)
echo [1/6] 安裝需要的套件 openpyxl ...
python -m pip install -q openpyxl
echo [2/6] 利基排名 ...
python scripts\shopee_niche_scorer.py
echo [3/6] 連結批次表 + 好物清單頁 ...
python scripts\shopee_link_builder.py
echo [4/6] 貼文草稿 + 30 天排程 ...
python scripts\shopee_post_generator.py
echo [5/6] 營運追蹤表 tracker.xlsx ...
python scripts\shopee_tracker.py
echo [6/6] 收入模型 ...
python scripts\shopee_roi_calc.py
echo.
echo ==========================================
echo  完成！產出都在 shopee-affiliate\ 資料夾：
echo    tracker.xlsx          營運追蹤表（會自動打開）
echo    posts\                貼文草稿、schedule.csv
echo    reports\              利基排名、批次表、發文日曆、收入模型
echo    linkpage\index.html   好物清單頁（雙擊可預覽）
echo ==========================================
start "" "%~dp0tracker.xlsx"
echo.
pause
