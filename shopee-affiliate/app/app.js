/* 蝦皮分潤助手 — 單檔前端應用（手機 / 電腦）
 * 資料存在瀏覽器 localStorage，可選擇同步到 GitHub repo 的 data.json（和自動發文機器人共用）。
 * 不需要後端。token 只存在這台裝置的 localStorage，不會寫進 data.json。
 */
"use strict";

const DATA_URL = "data.json";
const LS_DATA = "sa_data_v1";
const LS_TOKEN = "sa_gh_token";
const LS_VIEW = "sa_view";

const PLATFORMS = {
  threads: { label: "Threads", code: "th" },
  instagram: { label: "Instagram", code: "ig" },
  shopee_video: { label: "蝦皮影音", code: "sv" },
};

const TEMPLATES = {
  threads: {
    hot_take: { label: "反直覺觀點", body: `{hot_take}

我自己{pain_point}很久，網路上教的方法幾乎都試過，沒一個撐過一個月。
後來隨便買了個{name}，{sp1}，反而是最便宜的那個有用。

不懂為什麼都沒人講這個。` },
    rant: { label: "抱怨文", body: `{pain_point}這件事到底還要困擾我多久

認真問，大家都怎麼解的？
我目前是靠{name}撐著，{sp1}，算解了一半。
有更好的方法拜託告訴我 🙏` },
    confession: { label: "真心話", body: `老實說{name}我一開始覺得超雞肋。

用了兩週收回這句話。{sp1}，{sp2}，最有感的是{sp3}。
缺點也有：（這裡寫一個真實的小缺點，例如顏色很醜、組裝要十分鐘）

{audience}應該會懂我在說什麼。` },
    question: { label: "丟問題", body: `{audience}真的有人沒遇過{pain_point}嗎？

我不信。
我是靠{name}才解決的，{sp1}。
你們是怎麼活下來的，還是直接放棄治療？` },
    before_after: { label: "前後對比", body: `以前：{pain_point}
現在：{sp1}

中間只差一個{name}，笑死，早買早享受。
對比照在第二張。` },
    campaign: { label: "檔期提醒", body: `平常不會特別講，但{name}這波有降價（這裡填折扣或券）。

{pain_point}的人，我只提醒這一次。` },
  },
  instagram: {
    carousel: { label: "輪播圖文", body: `【{category}】{name}｜{sp1}

{pain_point}？這個我用了之後真的有差。

📌 {sp1}
📌 {sp2}
📌 {sp3}

💰 NT\${price}
🔗 連結在個人檔案的「好物清單」

{disclosure}

.
.
.
#蝦皮好物 #{category} #好物分享 #租屋 #生活好物 #開箱 #蝦皮分潤 #小資生活 #居家 #實測` },
    reels: { label: "Reels 文案", body: `{pain_point}？我找到解法了 👉 {name}

{sp1}｜{sp2}｜{sp3}
NT\${price}

完整連結在個人檔案 🔗

{disclosure}

#蝦皮好物 #{category} #好物推薦 #開箱 #reels #小資生活` },
  },
  shopee_video: {
    demo_15s: { label: "15 秒實測", body: `【0-2 秒 鉤子】
字卡：{pain_point}？
畫面：直接拍問題的現場

【2-10 秒 解法】
字卡：{name}
畫面：拿出商品 → 使用 → 立刻看到結果
旁白：{sp1}，{sp2}

【10-13 秒 補一刀】
字卡：{sp3}
畫面：細節特寫

【13-15 秒 CTA】
字卡：NT\${price}，連結在商品卡 👇

備註：{disclosure}` },
    compare_30s: { label: "30 秒對比", body: `【0-3 秒】字卡：「以前 vs 現在」
【3-12 秒】以前：{pain_point}（拍 2-3 個真實困擾畫面）
【12-24 秒】現在：{name}，{sp1}、{sp2}、{sp3}（每個賣點配一個畫面）
【24-27 秒】真心話：說一個小缺點，再說為什麼還是推
【27-30 秒】CTA：NT\${price}，{audience}可以試試，商品連結在下面 👇

備註：{disclosure}` },
  },
};

const DEFAULT_SETTINGS = {
  timezone: "Asia/Taipei",
  link_mode: "reply",
  autopost: { threads: false },
  platforms: { threads: true, instagram: true, shopee_video: false },
  slots: { threads: ["09:00", "21:00"], instagram: ["20:00"], shopee_video: ["19:00"] },
  goals: { month_1_commission_twd: 500, month_3_commission_twd: 5000, month_6_commission_twd: 20000 },
  withdrawn_total: 0,
  sub_id_pattern: "{platform}_{niche}_{yyyymm}_{product_id}",
  github: { owner: "", repo: "", branch: "", path: "shopee-affiliate/app/data.json", autosync: false },
};

let state = null;
let dirty = false;
let pushTimer = null;
let currentView = "today";
let postsPreselect = null;

// ── 小工具 ───────────────────────────────────────────────────────
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => "NT$" + Math.round(Number(n) || 0).toLocaleString("zh-TW");
const pad2 = (n) => String(n).padStart(2, "0");
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
function localDate(d = new Date()) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`; }
const todayStr = () => localDate();
const monthKey = (iso) => String(iso).slice(0, 7);
const isoAt = (date, hhmm) => `${date}T${hhmm}:00+08:00`;
const isDue = (iso) => new Date(iso).getTime() <= Date.now();
const weekday = (date) => "日一二三四五六"[new Date(date + "T00:00:00").getDay()];

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 2200);
}
function openModal(title, html, onMount) {
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = html;
  $("#modal").hidden = false;
  document.body.style.overflow = "hidden";
  if (onMount) onMount($("#modal-body"));
}
function closeModal() { $("#modal").hidden = true; document.body.style.overflow = ""; }

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("已複製"); }
  catch { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); toast("已複製"); }
}
function armConfirm(btn, fn, label = "再按一次確認") {
  if (btn.dataset.armed) { delete btn.dataset.armed; btn.classList.remove("danger"); fn(); return; }
  btn.dataset.armed = "1"; const orig = btn.innerHTML; btn.innerHTML = label; btn.classList.add("danger");
  setTimeout(() => { if (btn.isConnected && btn.dataset.armed) { delete btn.dataset.armed; btn.innerHTML = orig; btn.classList.remove("danger"); } }, 3000);
}
function download(filename, text) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  a.download = filename; a.click(); URL.revokeObjectURL(a.href);
}

// ── 資料 ─────────────────────────────────────────────────────────
function normalize(d) {
  d = d && typeof d === "object" ? d : {};
  d.version = 1;
  d.brand = Object.assign({ account_name: "蝦皮分潤助手", handle: "", tagline: "", disclosure: "這是蝦皮分潤連結，用它買我會拿到一點回饋，你的價格不變。" }, d.brand || {});
  const s = d.settings || {};
  d.settings = {
    ...DEFAULT_SETTINGS, ...s,
    autopost: { ...DEFAULT_SETTINGS.autopost, ...(s.autopost || {}) },
    platforms: { ...DEFAULT_SETTINGS.platforms, ...(s.platforms || {}) },
    slots: { ...DEFAULT_SETTINGS.slots, ...(s.slots || {}) },
    goals: { ...DEFAULT_SETTINGS.goals, ...(s.goals || {}) },
    github: { ...DEFAULT_SETTINGS.github, ...(s.github || {}) },
  };
  d.products = (d.products || []).map((p) => ({ id: p.id || uid(), niche: p.niche || "home", category: p.category || "", name: p.name || "", price: Number(p.price) || 0, pct: Number(p.pct) || 0, selling_points: Array.isArray(p.selling_points) ? p.selling_points : String(p.selling_points || "").split("|").map((x) => x.trim()).filter(Boolean), pain_point: p.pain_point || "", hot_take: p.hot_take || "", audience: p.audience || "", shopee_url: p.shopee_url || "", affiliate_link: p.affiliate_link || "", status: p.status || "idea", notes: p.notes || "" }));
  d.schedule = (d.schedule || []).map((x) => ({ id: x.id || uid(), datetime: x.datetime, platform: x.platform || "threads", product_id: x.product_id || "", type: x.type || "", type_label: x.type_label || "", sub_id: x.sub_id || "", text: x.text || "", link: x.link || "", status: x.status || "scheduled", auto: x.auto !== false, posted_id: x.posted_id || "", posted_at: x.posted_at || "", error: x.error || "" }));
  d.daily = (d.daily || []).map((x) => ({ date: x.date, clicks: Number(x.clicks) || 0, orders: Number(x.orders) || 0, revenue: Number(x.revenue) || 0, commission: Number(x.commission) || 0, note: x.note || "" }));
  d.updated_at = d.updated_at || new Date().toISOString();
  return d;
}

async function load() {
  let raw = null; try { raw = localStorage.getItem(LS_DATA); } catch {}
  if (raw) { try { state = normalize(JSON.parse(raw)); return; } catch { /* fallthrough */ } }
  if (window.ARTIFACT_BUILD && window.SEED_DATA) { state = normalize(JSON.parse(JSON.stringify(window.SEED_DATA))); try { localStorage.setItem(LS_DATA, JSON.stringify(state)); } catch {} return; }
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    state = normalize(await res.json());
    localStorage.setItem(LS_DATA, JSON.stringify(state));
  } catch (e) {
    if (window.SEED_DATA) { state = normalize(JSON.parse(JSON.stringify(window.SEED_DATA))); localStorage.setItem(LS_DATA, JSON.stringify(state)); }
    else { state = normalize({}); toast("載入 data.json 失敗，先用空白資料"); }
  }
}

function save(markDirty = true) {
  state.updated_at = new Date().toISOString();
  try { localStorage.setItem(LS_DATA, JSON.stringify(state)); } catch {}
  if (markDirty) { dirty = true; if (ghReady() && state.settings.github.autosync) schedulePush(); if (cloud) cloudPush(); }
  renderSyncState();
}

function productById(id) { return state.products.find((p) => p.id === id); }

// ── 模板 ─────────────────────────────────────────────────────────
function templateVars(p) {
  const sps = [...(p.selling_points || [])]; while (sps.length < 3) sps.push("（補一個賣點）");
  return { name: p.name, price: p.price, sp1: sps[0], sp2: sps[1], sp3: sps[2], pain_point: p.pain_point, hot_take: p.hot_take || "（這裡寫一句反直覺的觀點）", audience: p.audience, category: p.category, link: p.affiliate_link || "（分潤連結待補）", disclosure: state.brand.disclosure, account: state.brand.handle };
}
function renderTemplate(body, vars) { return body.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)); }
function subIdFor(platform, p, date) {
  return state.settings.sub_id_pattern.replace("{platform}", PLATFORMS[platform].code).replace("{niche}", p.niche).replace("{yyyymm}", date.slice(0, 7).replace("-", "")).replace("{product_id}", p.id).toLowerCase().replace(/[^a-z0-9_]/g, "_");
}
function replyText(item) {
  const link = item.link || productById(item.product_id)?.affiliate_link || "";
  return [link, state.brand.disclosure].filter(Boolean).join("\n");
}
function composeForShare(item) {
  const link = item.link || productById(item.product_id)?.affiliate_link || "";
  return state.settings.link_mode === "inline" && link ? `${item.text}\n${link}` : item.text;
}

// ── 畫面切換 ─────────────────────────────────────────────────────
function setView(name) {
  currentView = name; try { localStorage.setItem(LS_VIEW, name); } catch {}
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  render();
  window.scrollTo(0, 0);
}
function render() {
  ({ today: renderToday, products: renderProducts, posts: renderPosts, data: renderData, settings: renderSettings })[currentView]();
  $("#brand-name").textContent = state.brand.account_name || "蝦皮分潤助手";
  renderSyncState();
}

// ── 今日 ─────────────────────────────────────────────────────────
function monthStats(mk) {
  const rows = state.daily.filter((d) => monthKey(d.date) === mk);
  const sum = (k) => rows.reduce((a, r) => a + r[k], 0);
  return { clicks: sum("clicks"), orders: sum("orders"), revenue: sum("revenue"), commission: sum("commission"), days: rows.length };
}
function postCard(item, opts = {}) {
  const p = productById(item.product_id) || { name: "（商品已刪除）" };
  const link = item.link || p.affiliate_link || "";
  const statusChip = { scheduled: "", posted: '<span class="chip ok">✅ 已發佈</span>', error: `<span class="chip bad">⚠️ 失敗</span>`, skipped: '<span class="chip">跳過</span>' }[item.status] || "";
  const overdue = item.status === "scheduled" && isDue(item.datetime) && item.datetime.slice(0, 10) < todayStr();
  return `<div class="card ${item.status !== "scheduled" ? "pending" : ""}" data-id="${item.id}">
    <div class="row between">
      <div class="row"><span class="chip ${item.platform}">${PLATFORMS[item.platform]?.label || item.platform}</span><span class="chip">${esc(item.type_label || item.type)}</span>${statusChip}${overdue ? '<span class="chip warn">逾期</span>' : ""}</div>
      <span class="time">${item.datetime.slice(0, 10)} ${item.datetime.slice(11, 16)}</span>
    </div>
    <h3 style="margin:8px 0 6px">${esc(p.name)}</h3>
    ${item.error ? `<div class="alert bad">⚠️ ${esc(item.error)}</div>` : ""}
    <div class="post-text" data-toggle>${esc(item.text)}</div>
    <div class="actions">
      <button class="btn sm" data-act="copy">📋 複製文案</button>
      ${link ? (item.platform === "threads" ? `<button class="btn sm" data-act="copyreply">💬 複製留言（連結＋揭露）</button>` : `<button class="btn sm" data-act="copylink">🔗 複製連結</button>`) : `<span class="chip warn">待補分潤連結</span>`}
      ${item.platform === "threads" ? `<a class="btn sm" target="_blank" rel="noopener" href="https://www.threads.net/intent/post?text=${encodeURIComponent(composeForShare(item))}">🧵 開 Threads 發文</a>` : ""}
      ${navigator.share && !window.ARTIFACT_BUILD ? `<button class="btn sm" data-act="share">📤 分享</button>` : ""}
      ${item.status === "scheduled" ? `<button class="btn sm primary" data-act="posted">✅ 已發佈</button><button class="btn sm ghost" data-act="skip">跳過</button>` : ""}
      <button class="btn sm ghost" data-act="edit">✏️</button>
      ${opts.allowDelete ? `<button class="btn sm ghost" data-act="delete">🗑</button>` : ""}
    </div>
  </div>`;
}
function bindPostCards(container, afterChange) {
  container.addEventListener("click", async (e) => {
    const card = e.target.closest("[data-id]"); if (!card) return;
    const item = state.schedule.find((s) => s.id === card.dataset.id); if (!item) return;
    if (e.target.closest("[data-toggle]")) { e.target.closest("[data-toggle]").classList.toggle("open"); return; }
    const act = e.target.closest("[data-act]")?.dataset.act; if (!act) return;
    const p = productById(item.product_id) || {};
    const link = item.link || p.affiliate_link || "";
    if (act === "copy") copyText(composeForShare(item));
    if (act === "copylink") copyText(link);
    if (act === "copyreply") copyText(replyText(item));
    if (act === "share") { try { await navigator.share({ text: composeForShare(item) }); } catch (err) { if (err && err.name !== "AbortError") { await copyText(composeForShare(item)); toast("這裡不支援系統分享，文案已複製"); } } }
    if (act === "posted") { item.status = "posted"; item.posted_at = new Date().toISOString(); save(); toast("已標記為已發佈"); afterChange(); }
    if (act === "skip") { item.status = "skipped"; save(); afterChange(); }
    if (act === "delete") armConfirm(e.target.closest("[data-act]"), () => { state.schedule = state.schedule.filter((s) => s.id !== item.id); save(); afterChange(); }, "確定刪除？");
    if (act === "edit") editPostModal(item, afterChange);
  });
}
function editPostModal(item, afterChange) {
  openModal("編輯貼文", `
    <div class="field"><label>發文時間</label><input type="datetime-local" id="e-dt" value="${item.datetime.slice(0, 16)}"></div>
    <div class="field"><label>文案（Threads 上限 500 字）</label><textarea id="e-text">${esc(item.text)}</textarea><div class="hint"><span id="e-count">${item.text.length}</span> / 500</div></div>
    <div class="field"><label>連結（留空則用商品的分潤連結）</label><input id="e-link" value="${esc(item.link)}"></div>
    <div class="switch"><span>讓機器人自動發（只對 Threads 有效）</span><input type="checkbox" id="e-auto" ${item.auto ? "checked" : ""}></div>
    <div class="switch"><span>狀態</span><select id="e-status"><option value="scheduled">待發</option><option value="posted">已發佈</option><option value="skipped">跳過</option><option value="error">失敗</option></select></div>
    <div class="actions"><button class="btn primary block" id="e-save">儲存</button></div>`, (body) => {
    $("#e-status", body).value = item.status;
    $("#e-text", body).addEventListener("input", (e) => ($("#e-count", body).textContent = e.target.value.length));
    $("#e-save", body).onclick = () => {
      const dt = $("#e-dt", body).value; if (!dt) return toast("請填時間");
      item.datetime = dt + ":00+08:00"; item.text = $("#e-text", body).value; item.link = $("#e-link", body).value.trim();
      item.auto = $("#e-auto", body).checked; item.status = $("#e-status", body).value; if (item.status !== "error") item.error = "";
      state.schedule.sort((a, b) => a.datetime.localeCompare(b.datetime));
      save(); closeModal(); afterChange();
    };
  });
}
function renderToday() {
  const el = $("#view-today");
  const t = todayStr(); const mk = t.slice(0, 7); const ms = monthStats(mk);
  const due = state.schedule.filter((s) => s.status === "scheduled" && s.datetime.slice(0, 10) <= t).sort((a, b) => a.datetime.localeCompare(b.datetime));
  const upcoming = state.schedule.filter((s) => s.status === "scheduled" && s.datetime.slice(0, 10) > t).slice(0, 3);
  const hasLinks = state.products.some((p) => p.affiliate_link);
  el.innerHTML = `
    <div class="tiles" style="margin-bottom:14px">
      <div class="tile"><div class="label">今日待發</div><div class="value">${due.length}</div><div class="sub">${t}（${weekday(t)}）</div></div>
      <div class="tile"><div class="label">本月分潤</div><div class="value">${fmt(ms.commission)}</div><div class="sub">${ms.orders} 單 · ${ms.clicks} 點擊</div></div>
    </div>
    ${!hasLinks ? `<div class="alert warn">⚠️ 還沒有任何商品填分潤連結。到「選品」把後台產生的 s.shopee.tw 短連結填進去，貼文才有得點。</div>` : ""}
    ${!state.schedule.length ? `<div class="empty"><div class="big">✍️</div>還沒有排程。到「貼文」頁按「自動排程」。</div>` : ""}
    ${due.length ? `<div class="day-head">要發的</div>` + due.map((i) => postCard(i)).join("") : (state.schedule.length ? `<div class="empty"><div class="big">🎉</div>今天的都發完了</div>` : "")}
    ${upcoming.length ? `<div class="day-head">接下來</div>` + upcoming.map((i) => postCard(i)).join("") : ""}`;
  bindPostCards(el, renderToday);
}

// ── 選品 ─────────────────────────────────────────────────────────
function renderProducts() {
  const el = $("#view-products");
  const list = state.products;
  el.innerHTML = `
    <div class="row between" style="margin-bottom:10px"><h2 style="margin:0">選品庫 <span class="muted small">${list.length} 個</span></h2><button class="btn sm primary" id="p-add">＋ 新增商品</button></div>
    ${list.length ? list.map((p) => `
      <div class="card" data-pid="${p.id}">
        <div class="row between"><div class="row"><span class="chip">${esc(p.id)}</span><span class="chip">${esc(p.category || p.niche)}</span><span class="chip ${p.status === "live" ? "ok" : p.status === "paused" ? "bad" : ""}">${esc(p.status)}</span></div><span class="price">${fmt(p.price)} · ${p.pct}%</span></div>
        <h3 style="margin:8px 0 4px">${esc(p.name)}</h3>
        <div class="small muted">${esc(p.pain_point)}</div>
        <div class="small" style="margin-top:4px">${p.selling_points.map(esc).join(" · ")}</div>
        <div class="small" style="margin-top:6px">${p.affiliate_link ? `<span class="chip ok">🔗 有分潤連結</span>` : `<span class="chip warn">待補分潤連結</span>`} <span class="muted">每單約 ${fmt(Math.min(p.price * p.pct / 100, 500))}</span></div>
        <div class="actions">
          <button class="btn sm" data-act="edit">✏️ 編輯</button>
          <button class="btn sm" data-act="gen">✍️ 產生貼文</button>
          ${p.affiliate_link ? `<button class="btn sm" data-act="copylink">🔗 複製連結</button>` : ""}
          ${(p.affiliate_link || p.shopee_url) ? `<a class="btn sm ghost" target="_blank" rel="noopener" href="${esc(p.affiliate_link || p.shopee_url)}">開賣場</a>` : ""}
        </div>
      </div>`).join("") : `<div class="empty"><div class="big">🛒</div>還沒有商品</div>`}`;
  $("#p-add", el).onclick = () => productForm(null);
  el.addEventListener("click", (e) => {
    const card = e.target.closest("[data-pid]"); const act = e.target.closest("[data-act]")?.dataset.act; if (!card || !act) return;
    const p = productById(card.dataset.pid);
    if (act === "edit") productForm(p);
    if (act === "copylink") copyText(p.affiliate_link);
    if (act === "gen") { postsPreselect = p.id; setView("posts"); }
  });
}
function productForm(p) {
  const isNew = !p;
  p = p || { id: "P" + String(state.products.length + 1).padStart(3, "0"), niche: "home", category: "", name: "", price: 0, pct: 1, selling_points: [], pain_point: "", hot_take: "", audience: "", shopee_url: "", affiliate_link: "", status: "idea", notes: "" };
  openModal(isNew ? "新增商品" : "編輯商品", `
    <div class="inline-fields">
      <div class="field"><label>ID</label><input id="f-id" value="${esc(p.id)}" ${isNew ? "" : "readonly"}></div>
      <div class="field"><label>利基代碼</label><input id="f-niche" value="${esc(p.niche)}" placeholder="home / desk / kitchen"></div>
      <div class="field"><label>分類</label><input id="f-category" value="${esc(p.category)}"></div>
    </div>
    <div class="field"><label>商品名稱</label><input id="f-name" value="${esc(p.name)}"></div>
    <div class="inline-fields">
      <div class="field"><label>售價 NT$</label><input id="f-price" type="number" inputmode="decimal" value="${p.price}"></div>
      <div class="field"><label>分潤率 %</label><input id="f-pct" type="number" inputmode="decimal" step="0.1" value="${p.pct}"></div>
      <div class="field"><label>狀態</label><select id="f-status"><option>idea</option><option>ready</option><option>live</option><option>paused</option></select></div>
    </div>
    <div class="field"><label>賣點（一行一個，3 個最好）</label><textarea id="f-sp" style="min-height:90px">${esc(p.selling_points.join("\n"))}</textarea></div>
    <div class="field"><label>痛點（一句話）</label><input id="f-pain" value="${esc(p.pain_point)}"></div>
    <div class="field"><label>爭議句 / 反直覺觀點（Threads 第一行）</label><input id="f-hot" value="${esc(p.hot_take || "")}" placeholder="例：租屋族買收納用品九成是智商稅"><div class="hint">像在跟朋友嗆聲的一句話，沒有這句 Threads 很難被推</div></div>
    <div class="field"><label>受眾</label><input id="f-aud" value="${esc(p.audience)}"></div>
    <div class="field"><label>蝦皮商品網址</label><input id="f-url" value="${esc(p.shopee_url)}" placeholder="https://shopee.tw/..."></div>
    <div class="field"><label>分潤短連結（後台產生）</label><input id="f-aff" value="${esc(p.affiliate_link)}" placeholder="https://s.shopee.tw/..."><div class="hint">到 affiliate.shopee.tw 後台「商品連結產生器」貼網址 + sub_id 取得</div></div>
    <div class="field"><label>備註</label><input id="f-notes" value="${esc(p.notes)}"></div>
    <div class="actions"><button class="btn primary" id="f-save" style="flex:1">儲存</button>${isNew ? "" : `<button class="btn ghost" id="f-del">刪除</button>`}</div>`, (body) => {
    $("#f-status", body).value = p.status;
    $("#f-save", body).onclick = () => {
      const id = $("#f-id", body).value.trim(); if (!id || !$("#f-name", body).value.trim()) return toast("ID 與名稱必填");
      if (isNew && productById(id)) return toast("ID 重複");
      Object.assign(p, { id, niche: $("#f-niche", body).value.trim() || "home", category: $("#f-category", body).value.trim(), name: $("#f-name", body).value.trim(), price: Number($("#f-price", body).value) || 0, pct: Number($("#f-pct", body).value) || 0, status: $("#f-status", body).value, selling_points: $("#f-sp", body).value.split("\n").map((x) => x.trim()).filter(Boolean), pain_point: $("#f-pain", body).value.trim(), hot_take: $("#f-hot", body).value.trim(), audience: $("#f-aud", body).value.trim(), shopee_url: $("#f-url", body).value.trim(), affiliate_link: $("#f-aff", body).value.trim(), notes: $("#f-notes", body).value.trim() });
      if (isNew) state.products.push(p);
      // 商品連結更新時，同步到還沒發的排程
      state.schedule.forEach((s) => { if (s.product_id === p.id && s.status === "scheduled" && !s.link) s.link = p.affiliate_link; });
      save(); closeModal(); render(); toast("已儲存");
    };
    const del = $("#f-del", body); if (del) del.onclick = () => armConfirm(del, () => { state.products = state.products.filter((x) => x.id !== p.id); save(); closeModal(); render(); }, "確定刪除？");
  });
}

// ── 貼文 ─────────────────────────────────────────────────────────
function nextSlot(platform) {
  const slots = state.settings.slots[platform] || ["09:00"];
  const taken = new Set(state.schedule.filter((s) => s.platform === platform && s.status === "scheduled").map((s) => s.datetime.slice(0, 16)));
  const d = new Date();
  for (let i = 0; i < 60; i++) {
    const date = localDate(new Date(d.getFullYear(), d.getMonth(), d.getDate() + i));
    for (const hhmm of slots) {
      const iso = isoAt(date, hhmm);
      if (!isDue(iso) && !taken.has(iso.slice(0, 16))) return iso;
    }
  }
  return isoAt(localDate(new Date(d.getTime() + 864e5)), slots[0]);
}
function autoSchedule(startDate, days) {
  const platforms = Object.keys(PLATFORMS).filter((k) => state.settings.platforms[k] && (state.settings.slots[k] || []).length);
  const products = state.products.filter((p) => p.status !== "paused");
  if (!platforms.length || !products.length) return 0;
  const taken = new Set(state.schedule.map((s) => s.datetime.slice(0, 16) + s.platform));
  let pi = 0; const ti = {}; let n = 0;
  const base = new Date(startDate + "T00:00:00");
  for (let d = 0; d < days; d++) {
    const date = localDate(new Date(base.getFullYear(), base.getMonth(), base.getDate() + d));
    for (const pf of platforms) {
      const types = Object.keys(TEMPLATES[pf]); ti[pf] = ti[pf] || 0;
      for (const hhmm of state.settings.slots[pf]) {
        const iso = isoAt(date, hhmm);
        if (taken.has(iso.slice(0, 16) + pf) || isDue(iso)) continue;
        const p = products[pi++ % products.length]; const type = types[ti[pf]++ % types.length];
        state.schedule.push({ id: uid(), datetime: iso, platform: pf, product_id: p.id, type, type_label: TEMPLATES[pf][type].label, sub_id: subIdFor(pf, p, date), text: renderTemplate(TEMPLATES[pf][type].body, templateVars(p)), link: p.affiliate_link, status: "scheduled", auto: pf === "threads", posted_id: "", posted_at: "", error: "" });
        n++;
      }
    }
  }
  state.schedule.sort((a, b) => a.datetime.localeCompare(b.datetime));
  return n;
}
let postsFilter = "scheduled";
function renderPosts() {
  const el = $("#view-posts");
  const products = state.products;
  const selP = postsPreselect || products[0]?.id || ""; postsPreselect = null;
  const upcoming = state.schedule.filter((s) => postsFilter === "all" || s.status === postsFilter).sort((a, b) => (postsFilter === "posted" ? b.datetime.localeCompare(a.datetime) : a.datetime.localeCompare(b.datetime)));
  const groups = {}; upcoming.forEach((s) => (groups[s.datetime.slice(0, 10)] = groups[s.datetime.slice(0, 10)] || []).push(s));
  const counts = { scheduled: 0, posted: 0, error: 0, skipped: 0 }; state.schedule.forEach((s) => (counts[s.status] = (counts[s.status] || 0) + 1));
  el.innerHTML = `
    <div class="card">
      <h2>產生貼文</h2>
      <div class="inline-fields">
        <div class="field"><label>商品</label><select id="g-product">${products.map((p) => `<option value="${esc(p.id)}" ${p.id === selP ? "selected" : ""}>${esc(p.id)} ${esc(p.name)}</option>`).join("")}</select></div>
        <div class="field"><label>平台</label><select id="g-platform">${Object.entries(PLATFORMS).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join("")}</select></div>
        <div class="field"><label>類型</label><select id="g-type"></select></div>
      </div>
      <div class="field"><label>主文（可直接改）</label><textarea id="g-text"></textarea><div class="hint"><span id="g-count">0</span> / 500 · Threads 主文不放價格、不放連結、不放揭露；第一行改成自己的口氣</div></div>
      <div class="field" id="g-reply-wrap"><label>第一則留言（主文發完馬上回）</label><textarea id="g-reply" readonly style="min-height:70px"></textarea></div>
      <div class="field"><label>發文時間</label><input type="datetime-local" id="g-dt"></div>
      <div class="actions"><button class="btn primary" id="g-add" style="flex:1">＋ 加入排程</button><button class="btn" id="g-copy">📋 複製</button></div>
    </div>
    <div class="card">
      <h2>自動排程</h2>
      <div class="small muted" style="margin-bottom:8px">用設定裡的時段，把商品與貼文類型輪流排好。已排的時段不會重複。</div>
      <div class="inline-fields">
        <div class="field"><label>從</label><input type="date" id="a-start" value="${todayStr()}"></div>
        <div class="field"><label>天數</label><input type="number" id="a-days" value="14" min="1" max="60"></div>
      </div>
      <div class="actions"><button class="btn primary" id="a-run" style="flex:1">⚡ 自動排 ${Object.keys(PLATFORMS).filter((k) => state.settings.platforms[k]).map((k) => PLATFORMS[k].label).join(" + ")}</button><button class="btn ghost" id="a-clear">清除所有待發</button></div>
      <div class="hint" style="margin-top:6px">模板改版後，先「清除所有待發」再重新自動排，舊草稿才會換成新風格。</div>
    </div>
    <div class="row" style="margin:14px 0 6px">
      ${[["scheduled", "待發"], ["posted", "已發"], ["error", "失敗"], ["skipped", "跳過"], ["all", "全部"]].map(([k, l]) => `<button class="btn sm ${postsFilter === k ? "primary" : ""}" data-filter="${k}">${l}${k !== "all" ? ` ${counts[k] || 0}` : ""}</button>`).join("")}
    </div>
    <div id="g-list">${Object.keys(groups).length ? Object.entries(groups).map(([date, items]) => `<div class="day-head">${date}（${weekday(date)}）</div>` + items.map((i) => postCard(i, { allowDelete: true })).join("")).join("") : `<div class="empty">沒有項目</div>`}</div>`;

  const selType = $("#g-type", el), selPf = $("#g-platform", el), selProd = $("#g-product", el), ta = $("#g-text", el), dt = $("#g-dt", el), count = $("#g-count", el);
  function fillTypes() { selType.innerHTML = Object.entries(TEMPLATES[selPf.value]).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join(""); }
  function fillText() { const p = productById(selProd.value); if (!p) return; ta.value = renderTemplate(TEMPLATES[selPf.value][selType.value].body, templateVars(p)); count.textContent = ta.value.length; dt.value = nextSlot(selPf.value).slice(0, 16);
    const rw = $("#g-reply-wrap", el); rw.hidden = selPf.value !== "threads"; $("#g-reply", el).value = [p.affiliate_link || "（分潤連結待補）", state.brand.disclosure].join("\n"); }
  fillTypes(); fillText();
  selPf.onchange = () => { fillTypes(); fillText(); }; selType.onchange = fillText; selProd.onchange = fillText;
  ta.oninput = () => (count.textContent = ta.value.length);
  $("#g-copy", el).onclick = () => copyText(ta.value);
  $("#g-add", el).onclick = () => {
    const p = productById(selProd.value); if (!p) return toast("先新增商品"); if (!dt.value) return toast("請填時間");
    state.schedule.push({ id: uid(), datetime: dt.value + ":00+08:00", platform: selPf.value, product_id: p.id, type: selType.value, type_label: TEMPLATES[selPf.value][selType.value].label, sub_id: subIdFor(selPf.value, p, dt.value.slice(0, 10)), text: ta.value, link: p.affiliate_link, status: "scheduled", auto: selPf.value === "threads", posted_id: "", posted_at: "", error: "" });
    state.schedule.sort((a, b) => a.datetime.localeCompare(b.datetime)); save(); toast("已加入排程"); renderPosts();
  };
  $("#a-clear", el).onclick = (e) => armConfirm(e.currentTarget, () => { const n = state.schedule.filter((x) => x.status === "scheduled").length; state.schedule = state.schedule.filter((x) => x.status !== "scheduled"); save(); toast(`已清除 ${n} 篇待發`); renderPosts(); }, "確定清除？");
  $("#a-run", el).onclick = () => { const n = autoSchedule($("#a-start", el).value || todayStr(), Number($("#a-days", el).value) || 14); save(); toast(`已排 ${n} 篇`); renderPosts(); };
  $$("[data-filter]", el).forEach((b) => (b.onclick = () => { postsFilter = b.dataset.filter; renderPosts(); }));
  bindPostCards($("#g-list", el), renderPosts);
}

// ── 數據 ─────────────────────────────────────────────────────────
function renderData() {
  const el = $("#view-data");
  const t = todayStr(); const mk = t.slice(0, 7); const ms = monthStats(mk);
  const total = state.daily.reduce((a, r) => a + r.commission, 0);
  const unpaid = Math.max(0, total - (Number(state.settings.withdrawn_total) || 0));
  const goals = state.settings.goals;
  const cvr = ms.clicks ? (ms.orders / ms.clicks * 100) : 0;
  const perOrder = ms.orders ? ms.commission / ms.orders : 0;
  const rows = [...state.daily].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 31);
  const alerts = [];
  if (ms.commission >= 50000) alerts.push(`<div class="alert bad">🛑 本月分潤已達 NT$50,000，依規定需轉公司戶，詳見 05-請款稅務與合規.md</div>`);
  else if (ms.commission >= 40000) alerts.push(`<div class="alert warn">⚠️ 本月分潤接近 NT$50,000，開始準備公司戶</div>`);
  if (unpaid >= 500) alerts.push(`<div class="alert ok">✅ 累積未提領約 ${fmt(unpaid)}，已達 500 門檻，可到後台申請提領（提領後到設定填「已提領總額」）</div>`);
  const meter = (label, goal) => `<div class="small" style="margin-top:8px"><div class="row between"><span>${label}</span><span class="muted">${fmt(ms.commission)} / ${fmt(goal)}（${Math.min(100, Math.round(ms.commission / goal * 100))}%）</span></div><div class="meter"><span style="width:${Math.min(100, ms.commission / goal * 100)}%"></span></div></div>`;
  el.innerHTML = `
    ${alerts.join("")}
    <div class="tiles">
      <div class="tile"><div class="label">本月分潤</div><div class="value">${fmt(ms.commission)}</div><div class="sub">${mk}</div></div>
      <div class="tile"><div class="label">本月訂單</div><div class="value">${ms.orders}</div><div class="sub">${ms.clicks} 點擊</div></div>
      <div class="tile"><div class="label">轉換率</div><div class="value">${cvr.toFixed(1)}%</div><div class="sub">健康值 2-5%</div></div>
      <div class="tile"><div class="label">每單分潤</div><div class="value">${fmt(perOrder)}</div><div class="sub">太低就換加碼商品</div></div>
    </div>
    <div class="card" style="margin-top:12px">
      <h3>目標進度</h3>
      ${meter("第 1 個月目標", goals.month_1_commission_twd)}${meter("第 3 個月目標", goals.month_3_commission_twd)}${meter("第 6 個月目標", goals.month_6_commission_twd)}
      <div class="small muted" style="margin-top:8px">累計分潤 ${fmt(total)} · 已提領 ${fmt(state.settings.withdrawn_total)} · 未提領 ${fmt(unpaid)}</div>
    </div>
    <div class="card">
      <h3>記錄今天的後台數字</h3>
      <div class="inline-fields" style="margin-top:8px">
        <div class="field"><label>日期</label><input type="date" id="d-date" value="${t}"></div>
        <div class="field"><label>點擊</label><input type="number" inputmode="numeric" id="d-clicks" placeholder="0"></div>
        <div class="field"><label>訂單</label><input type="number" inputmode="numeric" id="d-orders" placeholder="0"></div>
        <div class="field"><label>訂單金額</label><input type="number" inputmode="numeric" id="d-rev" placeholder="0"></div>
        <div class="field"><label>分潤金</label><input type="number" inputmode="numeric" id="d-com" placeholder="0"></div>
      </div>
      <div class="field"><label>備註</label><input id="d-note" placeholder="例：P005 爆了"></div>
      <button class="btn primary block" id="d-save">儲存（同一天會覆蓋）</button>
    </div>
    <div class="card">
      <h3>最近 30 天</h3>
      <div class="table-wrap"><table><thead><tr><th>日期</th><th class="num">點擊</th><th class="num">訂單</th><th class="num">金額</th><th class="num">分潤</th><th></th></tr></thead><tbody>
        ${rows.length ? rows.map((r) => `<tr data-date="${r.date}"><td>${r.date.slice(5)}</td><td class="num">${r.clicks}</td><td class="num">${r.orders}</td><td class="num">${r.revenue.toLocaleString()}</td><td class="num">${r.commission.toLocaleString()}</td><td><button class="icon-btn" data-del title="刪除">🗑</button></td></tr>`).join("") : `<tr><td colspan="6" class="muted">還沒有數據。每天晚上把後台的數字填進來。</td></tr>`}
      </tbody></table></div>
    </div>`;
  $("#d-save", el).onclick = () => {
    const date = $("#d-date", el).value; if (!date) return toast("請選日期");
    const row = { date, clicks: Number($("#d-clicks", el).value) || 0, orders: Number($("#d-orders", el).value) || 0, revenue: Number($("#d-rev", el).value) || 0, commission: Number($("#d-com", el).value) || 0, note: $("#d-note", el).value.trim() };
    state.daily = state.daily.filter((r) => r.date !== date); state.daily.push(row); state.daily.sort((a, b) => a.date.localeCompare(b.date));
    save(); toast("已儲存"); renderData();
  };
  el.addEventListener("click", (e) => { const b = e.target.closest("[data-del]"); if (!b) return; const date = b.closest("tr").dataset.date; armConfirm(b, () => { state.daily = state.daily.filter((r) => r.date !== date); save(); renderData(); }, "確定？"); });
}

// ── 設定 ─────────────────────────────────────────────────────────
function renderSettings() {
  const el = $("#view-settings"); const s = state.settings; const b = state.brand; const gh = s.github; const token = localStorage.getItem(LS_TOKEN) || "";
  el.innerHTML = `
    <div class="card"><h2>帳號</h2>
      <div class="field"><label>帳號名稱</label><input id="s-name" value="${esc(b.account_name)}"></div>
      <div class="field"><label>Threads / IG 帳號</label><input id="s-handle" value="${esc(b.handle)}" placeholder="@..."></div>
      <div class="field"><label>一句話定位</label><input id="s-tag" value="${esc(b.tagline)}"></div>
      <div class="field"><label>揭露文字（每篇自動加）</label><textarea id="s-disc" style="min-height:70px">${esc(b.disclosure)}</textarea></div>
    </div>
    <div class="card"><h2>發文</h2>
      <div class="field"><label>連結放哪裡</label><select id="s-link"><option value="reply">第一則留言（推薦，機器人會自動回一則留言放連結）</option><option value="attach">貼文附連結卡片（link_attachment）</option><option value="inline">直接寫在文末</option></select></div>
      <div class="switch"><span>🤖 Threads 自動發文（需在 GitHub 設好 token，詳見 06 文件）</span><input type="checkbox" id="s-auto" ${s.autopost.threads ? "checked" : ""}></div>
      ${Object.entries(PLATFORMS).map(([k, v]) => `<div class="switch"><span>${v.label} 排程 <span class="muted small">時段 ${(s.slots[k] || []).join(", ")}</span></span><input type="checkbox" data-pf="${k}" ${s.platforms[k] ? "checked" : ""}></div>`).join("")}
      <div class="inline-fields" style="margin-top:8px">
        ${Object.entries(PLATFORMS).map(([k, v]) => `<div class="field"><label>${v.label} 時段（逗號分隔）</label><input data-slot="${k}" value="${esc((s.slots[k] || []).join(", "))}"></div>`).join("")}
      </div>
    </div>
    <div class="card"><h2>目標與提領</h2>
      <div class="inline-fields">
        <div class="field"><label>第 1 個月目標</label><input type="number" id="s-g1" value="${s.goals.month_1_commission_twd}"></div>
        <div class="field"><label>第 3 個月目標</label><input type="number" id="s-g3" value="${s.goals.month_3_commission_twd}"></div>
        <div class="field"><label>第 6 個月目標</label><input type="number" id="s-g6" value="${s.goals.month_6_commission_twd}"></div>
        <div class="field"><label>已提領總額</label><input type="number" id="s-wd" value="${s.withdrawn_total}"></div>
      </div>
    </div>
    ${window.ARTIFACT_BUILD ? `<div class="card"><h2>跨裝置</h2><div class="small muted">登入同一個 Claude 帳號開這個頁面，手機和電腦會自動用同一份資料（右上角顯示「雲端已同步」）。沒登入時只存在這台裝置，可用下面的匯出 / 匯入搬資料。Threads 自動發文機器人讀的是 GitHub 上的 data.json，要讓機器人發文，請把這裡匯出的 JSON 貼給 Claude 更新。</div></div>` : ""}
    <div class="card" ${window.ARTIFACT_BUILD ? "hidden" : ""}><h2>GitHub 同步 <span class="chip ${ghReady() ? "ok" : ""}">${ghReady() ? "已設定" : "未設定"}</span></h2>
      <div class="small muted" style="margin-bottom:8px">把資料存到 repo 的 data.json，手機和電腦就會同一份，自動發文機器人也讀這份。需要一個只有這個 repo「Contents 讀寫」權限的 fine-grained token。token 只存在這台裝置。</div>
      <div class="inline-fields">
        <div class="field"><label>owner</label><input id="s-owner" value="${esc(gh.owner)}" placeholder="Isaacmolt"></div>
        <div class="field"><label>repo</label><input id="s-repo" value="${esc(gh.repo)}" placeholder="-"></div>
        <div class="field"><label>branch</label><input id="s-branch" value="${esc(gh.branch)}" placeholder="claude/shopee-commission-planning-isbmsh"></div>
      </div>
      <div class="field"><label>path</label><input id="s-path" value="${esc(gh.path)}"></div>
      <div class="field"><label>token</label><input id="s-token" type="password" value="${esc(token)}" placeholder="github_pat_..." autocomplete="off"></div>
      <div class="switch"><span>改了就自動推送</span><input type="checkbox" id="s-autosync" ${gh.autosync ? "checked" : ""}></div>
      <div class="actions"><button class="btn" id="s-test">測試連線</button><button class="btn" id="s-pull">⬇️ 拉取</button><button class="btn primary" id="s-push">⬆️ 推送</button></div>
    </div>
    <div class="card"><h2>備份</h2>
      <div class="actions"><button class="btn" id="s-export">⬇️ 匯出 JSON</button><label class="btn">⬆️ 匯入 JSON<input type="file" id="s-import" accept="application/json" hidden></label><button class="btn ghost" id="s-reset">重設為 repo 的 data.json</button></div>
    </div>
    <div class="actions"><button class="btn primary block" id="s-save">儲存設定</button></div>
    <p class="small muted" style="text-align:center">蝦皮分潤助手 · 資料更新 ${new Date(state.updated_at).toLocaleString("zh-TW")}</p>`;
  $("#s-link", el).value = s.link_mode;
  const collect = () => {
    Object.assign(b, { account_name: $("#s-name", el).value.trim(), handle: $("#s-handle", el).value.trim(), tagline: $("#s-tag", el).value.trim(), disclosure: $("#s-disc", el).value.trim() });
    s.link_mode = $("#s-link", el).value; s.autopost.threads = $("#s-auto", el).checked;
    $$("[data-pf]", el).forEach((c) => (s.platforms[c.dataset.pf] = c.checked));
    $$("[data-slot]", el).forEach((i) => (s.slots[i.dataset.slot] = i.value.split(",").map((x) => x.trim()).filter((x) => /^\d{2}:\d{2}$/.test(x))));
    s.goals.month_1_commission_twd = Number($("#s-g1", el).value) || 0; s.goals.month_3_commission_twd = Number($("#s-g3", el).value) || 0; s.goals.month_6_commission_twd = Number($("#s-g6", el).value) || 0;
    s.withdrawn_total = Number($("#s-wd", el).value) || 0;
    Object.assign(gh, { owner: $("#s-owner", el).value.trim(), repo: $("#s-repo", el).value.trim(), branch: $("#s-branch", el).value.trim(), path: $("#s-path", el).value.trim() || "shopee-affiliate/app/data.json", autosync: $("#s-autosync", el).checked });
    const tk = $("#s-token", el).value.trim(); if (tk) localStorage.setItem(LS_TOKEN, tk); else localStorage.removeItem(LS_TOKEN);
  };
  $("#s-save", el).onclick = () => { collect(); save(); toast("已儲存"); render(); };
  $("#s-test", el).onclick = async () => { collect(); save(false); try { const r = await ghGet(); toast(`連線 OK，遠端有 ${r.data.schedule?.length ?? 0} 篇排程`); } catch (e) { toast("連線失敗：" + e.message); } };
  $("#s-pull", el).onclick = async () => { collect(); save(false); await pull(); };
  $("#s-push", el).onclick = async () => { collect(); save(); await push(); };
  $("#s-export", el).onclick = () => { const json = JSON.stringify(state, null, 2); openModal("匯出 JSON", `<div class="small muted" style="margin-bottom:8px">全選複製後存成 .json，或貼給 Claude。</div><div class="field"><textarea id="x-json" style="min-height:220px;font-family:ui-monospace,Menlo,monospace;font-size:.75rem">${esc(json)}</textarea></div><div class="actions"><button class="btn primary" id="x-copy" style="flex:1">📋 複製全部</button>${window.ARTIFACT_BUILD ? "" : `<button class="btn" id="x-dl">⬇️ 下載檔案</button>`}</div>`, (body) => { $("#x-copy", body).onclick = () => copyText(json); const dl = $("#x-dl", body); if (dl) dl.onclick = () => download(`shopee-affiliate-${todayStr()}.json`, json); }); };
  $("#s-import", el).onchange = async (e) => { const f = e.target.files[0]; if (!f) return; try { state = normalize(JSON.parse(await f.text())); save(); render(); toast("已匯入"); } catch { toast("檔案格式不對"); } };
  $("#s-reset", el).onclick = (e) => armConfirm(e.currentTarget, async () => { localStorage.removeItem(LS_DATA); await load(); render(); toast("已重設"); }, "會丟掉這台裝置的變更，再按一次確認");
}

// ── GitHub 同步 ──────────────────────────────────────────────────
function ghReady() { if (window.ARTIFACT_BUILD) return false; const g = state?.settings?.github; let t = null; try { t = localStorage.getItem(LS_TOKEN); } catch {} return !!(g && g.owner && g.repo && g.branch && g.path && t); }
function ghUrl() { const g = state.settings.github; return `https://api.github.com/repos/${g.owner}/${g.repo}/contents/${g.path}`; }
function ghHeaders() { return { Authorization: "Bearer " + localStorage.getItem(LS_TOKEN), Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" }; }
const b64encode = (str) => btoa(String.fromCharCode(...new TextEncoder().encode(str)));
const b64decode = (b64) => new TextDecoder().decode(Uint8Array.from(atob(b64.replace(/\n/g, "")), (c) => c.charCodeAt(0)));
async function ghGet() {
  if (!ghReady()) throw new Error("GitHub 尚未設定");
  const r = await fetch(`${ghUrl()}?ref=${encodeURIComponent(state.settings.github.branch)}`, { headers: ghHeaders(), cache: "no-store" });
  if (r.status === 404) return { sha: null, data: null };
  if (!r.ok) throw new Error(`GitHub ${r.status}`);
  const j = await r.json();
  return { sha: j.sha, data: JSON.parse(b64decode(j.content)) };
}
async function ghPut(data, sha) {
  const body = { message: "chore(app): update data.json from 蝦皮分潤助手 [skip ci]", content: b64encode(JSON.stringify(data, null, 2)), branch: state.settings.github.branch };
  if (sha) body.sha = sha;
  const r = await fetch(ghUrl(), { method: "PUT", headers: { ...ghHeaders(), "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) { const e = new Error(`GitHub ${r.status}`); e.status = r.status; throw e; }
  return (await r.json()).content.sha;
}
function merge(local, remote) {
  if (!remote) return local;
  const out = normalize(JSON.parse(JSON.stringify(local)));
  const rs = new Map((remote.schedule || []).map((s) => [s.id, s]));
  out.schedule = out.schedule.map((s) => { const r = rs.get(s.id); if (r && s.status === "scheduled" && ["posted", "error"].includes(r.status)) return { ...s, status: r.status, posted_id: r.posted_id || "", posted_at: r.posted_at || "", error: r.error || "" }; return s; });
  const ids = new Set(out.schedule.map((s) => s.id));
  (remote.schedule || []).forEach((r) => { if (!ids.has(r.id) && r.status !== "scheduled") out.schedule.push(r); });
  const dates = new Set(out.daily.map((d) => d.date));
  (remote.daily || []).forEach((r) => { if (!dates.has(r.date)) out.daily.push(r); });
  out.schedule.sort((a, b) => a.datetime.localeCompare(b.datetime)); out.daily.sort((a, b) => a.date.localeCompare(b.date));
  return out;
}
async function pull() {
  try {
    const { data } = await ghGet();
    if (!data) return toast("遠端還沒有 data.json，先推送一次");
    if (dirty) { state = merge(state, data); } else { state = normalize(data); }
    state.settings.github = { ...state.settings.github, ...(JSON.parse(localStorage.getItem(LS_DATA) || "{}").settings?.github || {}) };
    save(dirty); render(); toast(dirty ? "已合併遠端狀態" : "已拉取最新");
  } catch (e) { setSync("err", "拉取失敗"); toast("拉取失敗：" + e.message); }
}
async function push() {
  if (!ghReady()) { toast("先到設定填 GitHub 資訊"); return; }
  setSync("busy", "推送中…");
  try {
    let { sha, data } = await ghGet();
    let payload = merge(state, data);
    try { sha = await ghPut(payload, sha); }
    catch (e) { if (e.status === 409 || e.status === 422) { const again = await ghGet(); payload = merge(state, again.data); sha = await ghPut(payload, again.sha); } else throw e; }
    state = payload; dirty = false; save(false); renderSyncState(); toast("已推送到 GitHub");
  } catch (e) { setSync("err", "推送失敗"); toast("推送失敗：" + e.message); }
}
function schedulePush() { clearTimeout(pushTimer); pushTimer = setTimeout(push, 4000); }
function setSync(kind, label) { const d = $("#sync-dot"); d.className = "sync-dot " + (kind === "ok" ? "ok" : kind === "dirty" ? "dirty" : kind === "err" ? "err" : ""); $("#sync-label").textContent = label; }
function renderSyncState() {
  if (cloud || cloudState) return setCloud(dirty && cloudState === "ok" ? "busy" : cloudState);
  if (!ghReady()) return setSync("", "未同步");
  setSync(dirty ? "dirty" : "ok", dirty ? "有變更" : "已同步");
}


// ── claude.ai 跨裝置儲存（db capability；只有在 claude.ai 開啟時才會有 window.claude）──
let cloud = null, cloudWriting = null, cloudTimer = null, cloudLastWritten = "", cloudState = "";
function setCloud(kind) {
  cloudState = kind;
  const label = { ok: "雲端已同步", busy: "雲端儲存中…", err: "雲端儲存失敗", local: "僅存本機" }[kind] || "";
  if (label) setSync(kind === "ok" ? "ok" : kind === "busy" ? "dirty" : kind === "err" ? "err" : "", label);
}
function adoptRemote(d) {
  state = normalize(JSON.parse(JSON.stringify(d)));
  cloudLastWritten = state.updated_at;
  try { localStorage.setItem(LS_DATA, JSON.stringify(state)); } catch {}
  dirty = false; setCloud("ok"); render();
}
async function initCloud() {
  if (!(window.claude && typeof window.claude.use === "function")) return;
  let db = null;
  try { db = await window.claude.use("db"); } catch { db = null; }
  if (!db) { setCloud("local"); return; }
  const ref = db.doc("app/state");
  cloud = { db, ref };
  try {
    const snap = await ref.get();
    if (snap.exists && snap.data()?.updated_at && snap.data().updated_at > (state.updated_at || "")) adoptRemote(snap.data());
    else setCloud("ok");
  } catch (e) { setCloud("err"); return; }
  ref.onSnapshot((snap) => {
    if (!snap.exists || snap.metadata.hasPendingWrites) return;
    const d = snap.data();
    if (d && d.updated_at && d.updated_at !== cloudLastWritten && d.updated_at > (state.updated_at || "")) adoptRemote(d);
  }, () => setCloud("err"));
}
function cloudPush() {
  if (!cloud) return;
  clearTimeout(cloudTimer);
  cloudTimer = setTimeout(async () => {
    const payload = JSON.parse(JSON.stringify(state));
    const stamp = payload.updated_at;
    if (cloudWriting) { try { await cloudWriting; } catch {} }
    setCloud("busy");
    cloudWriting = cloud.ref.set(payload)
      .then(() => { cloudLastWritten = stamp; dirty = false; setCloud("ok"); })
      .catch((e) => { setCloud("err"); toast(["quota_exceeded", "invalid_argument"].includes(e?.code) ? "雲端儲存失敗：資料太大，請刪除舊的已發佈貼文" : "雲端儲存失敗，資料仍在這台裝置"); });
    try { await cloudWriting; } catch {} finally { cloudWriting = null; }
  }, 1500);
}

// ── 啟動 ─────────────────────────────────────────────────────────
async function init() {
  await load();
  $$(".tab").forEach((t) => (t.onclick = () => setView(t.dataset.view)));
  $$("[data-close]").forEach((b) => (b.onclick = closeModal));
  $("#sync-btn").onclick = () => { if (cloud) return toast(cloudState === "ok" ? "資料已自動同步到你的 Claude 帳號" : "雲端尚未同步，資料先存在這台裝置"); if (cloudState === "local") return toast("未登入 Claude，資料只存在這台裝置"); if (!ghReady()) return setView("settings"); dirty ? push() : pull(); };
  let v = "today"; try { v = localStorage.getItem(LS_VIEW) || "today"; } catch {}
  setView(v);
  if (ghReady() && state.settings.github.autosync) pull();
  if ("serviceWorker" in navigator && location.protocol.startsWith("http") && !window.ARTIFACT_BUILD) navigator.serviceWorker.register("sw.js").catch(() => {});
  initCloud();
}
init();
