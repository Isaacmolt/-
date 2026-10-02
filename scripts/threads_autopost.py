#!/usr/bin/env python3
"""
蝦皮分潤 — Threads 自動發文機器人

讀 shopee-affiliate/app/data.json 的排程，把「時間到了、平台是 threads、status=scheduled、auto=true」
的貼文透過 Threads 官方 API 發出去，然後把結果（posted / error）寫回 data.json。
由 .github/workflows/threads-autopost.yml 每小時跑一次；也可以在本機跑。

需要的環境變數：
    THREADS_ACCESS_TOKEN   Threads API 的長效 token（60 天，見 06 文件怎麼拿）
    THREADS_USER_ID        可省略，會用 /me 查

用法：
    python scripts/threads_autopost.py --dry-run          # 只列出會發什麼，不真的發
    python scripts/threads_autopost.py --limit 3          # 一次最多發 3 篇
    python scripts/threads_autopost.py --now 2026-10-06T09:05:00+08:00   # 假裝現在是這個時間（測試用）
    python scripts/threads_autopost.py --refresh-token    # 印出換新的長效 token

Threads API（graph.threads.net，以官方文件為準）：
    1. POST /v1.0/{user_id}/threads            media_type=TEXT, text, [link_attachment], [reply_to_id]
    2. GET  /v1.0/{container_id}?fields=status  等到 FINISHED
    3. POST /v1.0/{user_id}/threads_publish     creation_id
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "shopee-affiliate" / "app" / "data.json"
API = "https://graph.threads.net/v1.0"
TZ = timezone(timedelta(hours=8))
TEXT_LIMIT = 500


def api(method, path, params=None, token=None):
    params = dict(params or {})
    if token:
        params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path.lstrip('/')}"
    if method == "GET":
        url += "?" + data.decode()
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            msg = json.loads(body).get("error", {}).get("message", body)
        except Exception:
            msg = body
        raise RuntimeError(f"Threads API {e.code}: {msg}") from None


def get_user_id(token):
    return api("GET", "me", {"fields": "id,username"}, token)


def create_and_publish(user_id, token, text, link_attachment=None, reply_to_id=None):
    params = {"media_type": "TEXT", "text": text}
    if link_attachment:
        params["link_attachment"] = link_attachment
    if reply_to_id:
        params["reply_to_id"] = reply_to_id
    container = api("POST", f"{user_id}/threads", params, token)["id"]
    # 官方建議等伺服器處理完再 publish
    for _ in range(12):
        st = api("GET", container, {"fields": "status,error_message"}, token)
        if st.get("status") == "FINISHED":
            break
        if st.get("status") == "ERROR":
            raise RuntimeError(f"container error: {st.get('error_message')}")
        time.sleep(5)
    return api("POST", f"{user_id}/threads_publish", {"creation_id": container}, token)["id"]


def refresh_token(token):
    return api("GET", "../refresh_access_token", {"grant_type": "th_refresh_token"}, token)


def compose(item, data):
    link = (item.get("link") or "").strip()
    if not link:
        for p in data.get("products", []):
            if p.get("id") == item.get("product_id"):
                link = (p.get("affiliate_link") or "").strip()
                break
    mode = data.get("settings", {}).get("link_mode", "reply")
    text = (item.get("text") or "").strip()
    if mode == "inline" and link:
        text = f"{text}\n{link}"
    return text, link, mode


def main():
    parser = argparse.ArgumentParser(description="Threads 自動發文")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--now", default=None, help="ISO 時間，測試用")
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--refresh-token", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if args.refresh_token:
        if not token:
            sys.exit("缺 THREADS_ACCESS_TOKEN")
        r = refresh_token(token)
        print(r.get("access_token", ""))
        return

    data_path = Path(args.data)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(TZ)
    enabled = bool(data.get("settings", {}).get("autopost", {}).get("threads"))

    due = [s for s in data.get("schedule", [])
           if s.get("platform") == "threads" and s.get("status") == "scheduled" and s.get("auto", True)
           and datetime.fromisoformat(s["datetime"]) <= now]
    due.sort(key=lambda s: s["datetime"])

    print("=" * 70)
    print(f"Threads 自動發文｜現在 {now.isoformat(timespec='minutes')}｜自動發文開關：{'開' if enabled else '關'}｜到期 {len(due)} 篇")
    print("=" * 70)

    if not due:
        print("沒有到期的貼文。")
        return
    if not args.dry_run and not enabled:
        print("App 設定裡的「Threads 自動發文」是關的，什麼都不做。")
        return
    if not args.dry_run and not token:
        print("沒有 THREADS_ACCESS_TOKEN，什麼都不做。到 GitHub repo → Settings → Secrets 新增後才會發。")
        return

    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    if not args.dry_run and not user_id:
        me = get_user_id(token)
        user_id = me["id"]
        print(f"帳號：@{me.get('username')}（{user_id}）")

    posted = errors = 0
    for item in due[: args.limit]:
        text, link, mode = compose(item, data)
        head = f"[{item['datetime'][:16]}] {item.get('product_id')} {item.get('type_label', '')}"
        if len(text) > TEXT_LIMIT:
            item["status"], item["error"] = "error", f"文案 {len(text)} 字，超過 500 字上限"
            errors += 1
            print(f"✗ {head} → {item['error']}")
            continue
        if args.dry_run:
            print(f"· {head}\n  文案 {len(text)} 字｜連結模式 {mode}｜連結 {link or '（無）'}\n  " + text.replace("\n", "\n  ")[:200] + ("…" if len(text) > 200 else ""))
            continue
        try:
            media_id = create_and_publish(user_id, token, text, link_attachment=link if (mode == "attach" and link) else None)
            if mode == "reply" and link:
                try:
                    create_and_publish(user_id, token, f"🔗 {link}", reply_to_id=media_id)
                except Exception as e:  # 留言失敗不影響主貼文
                    print(f"  ⚠ 連結留言失敗：{e}")
            item.update({"status": "posted", "posted_id": media_id, "posted_at": datetime.now(TZ).isoformat(timespec="seconds"), "error": ""})
            posted += 1
            print(f"✓ {head} → {media_id}")
            time.sleep(3)
        except Exception as e:
            item["status"], item["error"] = "error", str(e)[:300]
            errors += 1
            print(f"✗ {head} → {e}")

    if not args.dry_run:
        data["updated_at"] = datetime.now(TZ).isoformat(timespec="seconds")
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("-" * 70)
        print(f"發佈 {posted} 篇，失敗 {errors} 篇，已寫回 {data_path.relative_to(BASE_DIR) if data_path.is_relative_to(BASE_DIR) else data_path}")


if __name__ == "__main__":
    main()
