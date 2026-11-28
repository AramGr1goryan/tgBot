# api/tasks_webapp.py
# Telegram Mini App (WebApp) for RobixLab Tasks Board
# Validated via Telegram WebApp initData HMAC-SHA256 signature.

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> Optional[Dict[str, Any]]:
    """Verify Telegram Mini App initData signature and return parsed user dict if valid."""
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    auth_date_raw = parsed.get("auth_date")
    if auth_date_raw:
        try:
            auth_date = int(auth_date_raw)
            if abs(int(time.time()) - auth_date) > max_age_seconds:
                return None
        except ValueError:
            return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    user_raw = parsed.get("user")
    if not user_raw:
        return None
    try:
        user = json.loads(user_raw)
    except Exception:
        return None

    if not isinstance(user, dict) or not user.get("id"):
        return None
    return user


TASKS_WEBAPP_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>RobixLab Tasks</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  :root {
    --bg: var(--tg-theme-bg-color, #0f1115);
    --surface: var(--tg-theme-secondary-bg-color, #181c24);
    --card: var(--tg-theme-section-bg-color, #1e232e);
    --text: var(--tg-theme-text-color, #f4f6fa);
    --hint: var(--tg-theme-hint-color, #8d96a8);
    --accent: var(--tg-theme-button-color, #3b82f6);
    --accent-text: var(--tg-theme-button-text-color, #ffffff);
    --sep: var(--tg-theme-section-separator-color, rgba(255,255,255,0.08));
    --crit: #ef4444;
    --crit-bg: rgba(239, 68, 68, 0.14);
    --high: #f59e0b;
    --high-bg: rgba(245, 158, 11, 0.15);
    --norm: #22c55e;
    --norm-bg: rgba(34, 197, 94, 0.14);
    --radius: 16px;
  }

  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

  html, body {
    margin: 0;
    padding: 0;
    min-height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Inter, sans-serif;
    -webkit-font-smoothing: antialiased;
  }

  body {
    padding: 16px 14px 104px;
    max-width: 600px;
    margin: 0 auto;
  }

  .hero {
    background: var(--surface);
    border: 1px solid var(--sep);
    border-radius: 20px;
    padding: 16px;
    margin-bottom: 14px;
  }

  .hero-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 12px;
  }

  .loc-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--accent);
    background: rgba(59, 130, 246, 0.12);
    padding: 4px 10px;
    border-radius: 999px;
    margin-bottom: 4px;
  }

  .title {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
  }

  .icon-btn {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    border: 1px solid var(--sep);
    background: var(--card);
    color: var(--text);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    cursor: pointer;
    flex-shrink: 0;
    transition: transform .15s ease, opacity .15s ease;
  }
  .icon-btn:active { transform: scale(0.92); opacity: 0.75; }
  .icon-btn.spin { animation: spin .65s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .prog-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: var(--hint);
    margin-bottom: 6px;
  }
  .prog-row strong { color: var(--text); font-weight: 700; }

  .prog-track {
    height: 6px;
    border-radius: 999px;
    background: var(--sep);
    overflow: hidden;
    margin-bottom: 12px;
  }
  .prog-fill {
    height: 100%;
    width: 0%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--accent), #22c55e);
    transition: width .35s cubic-bezier(.22,1,.36,1);
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .stat {
    background: var(--card);
    border: 1px solid var(--sep);
    border-radius: 12px;
    padding: 8px 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    transition: transform .15s ease, border-color .15s ease;
  }
  .stat:active { transform: scale(0.96); }
  .stat .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .stat.c .dot { background: var(--crit); box-shadow: 0 0 8px var(--crit); }
  .stat.h .dot { background: var(--high); box-shadow: 0 0 8px var(--high); }
  .stat.n .dot { background: var(--norm); box-shadow: 0 0 8px var(--norm); }
  .stat .lbl { font-size: 11px; color: var(--hint); font-weight: 600; margin-left: 6px; flex: 1; }
  .stat .num { font-size: 15px; font-weight: 800; }

  .tabs {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding: 2px 0 12px;
    scrollbar-width: none;
  }
  .tabs::-webkit-scrollbar { display: none; }

  .tab {
    flex: 0 0 auto;
    border: 1px solid var(--sep);
    background: var(--surface);
    color: var(--hint);
    font-size: 13px;
    font-weight: 700;
    padding: 8px 13px;
    border-radius: 999px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all .18s ease;
  }
  .tab .cnt {
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--sep);
  }
  .tab.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-text);
  }
  .tab.active .cnt { background: rgba(255,255,255,0.22); color: var(--accent-text); }
  .tab.active.tc { background: var(--crit); border-color: var(--crit); color: #fff; }
  .tab.active.th { background: var(--high); border-color: var(--high); color: #111; }
  .tab.active.th .cnt { background: rgba(0,0,0,0.16); color: #111; }
  .tab.active.tn { background: var(--norm); border-color: var(--norm); color: #052e16; }
  .tab.active.tn .cnt { background: rgba(0,0,0,0.14); color: #052e16; }

  .list { display: flex; flex-direction: column; gap: 10px; }

  .card {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: var(--surface);
    border: 1px solid var(--sep);
    border-radius: var(--radius);
    padding: 13px 13px 13px 16px;
    overflow: hidden;
    transition: transform .22s ease, opacity .25s ease;
  }
  .card::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: var(--norm);
  }
  .card.pC::before { background: var(--crit); }
  .card.pH::before { background: var(--high); }
  .card.pN::before { background: var(--norm); }

  .card.completing {
    opacity: 0.35;
    transform: translateX(18px) scale(0.98);
  }

  .chk {
    width: 24px;
    height: 24px;
    border-radius: 8px;
    border: 2px solid var(--hint);
    background: transparent;
    color: #fff;
    font-size: 14px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
    cursor: pointer;
    transition: all .16s ease;
  }
  .card.pC .chk { border-color: var(--crit); }
  .card.pH .chk { border-color: var(--high); }
  .card.pN .chk { border-color: var(--norm); }
  .chk:active { transform: scale(0.88); }
  .card.completing .chk { background: var(--norm); border-color: var(--norm); }

  .card-body { flex: 1; min-width: 0; }
  .card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 5px;
  }
  .tid {
    font-size: 12px;
    font-weight: 700;
    color: var(--hint);
    font-variant-numeric: tabular-nums;
  }
  .p-pill {
    border: 0;
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: transform .12s ease;
  }
  .p-pill:active { transform: scale(0.92); }
  .p-pill.C { background: var(--crit-bg); color: var(--crit); }
  .p-pill.H { background: var(--high-bg); color: var(--high); }
  .p-pill.N { background: var(--norm-bg); color: var(--norm); }

  .desc {
    font-size: 15px;
    line-height: 1.4;
    word-break: break-word;
    white-space: pre-wrap;
  }
  .card.completing .desc { text-decoration: line-through; color: var(--hint); }

  .empty {
    text-align: center;
    padding: 42px 20px;
    background: var(--surface);
    border: 1px dashed var(--sep);
    border-radius: 20px;
    color: var(--hint);
  }
  .empty .em { font-size: 38px; margin-bottom: 8px; }
  .empty .et { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
  .empty .es { font-size: 13px; }

  .fab {
    position: fixed;
    left: 14px;
    right: 14px;
    bottom: max(14px, env(safe-area-inset-bottom));
    max-width: 572px;
    margin: 0 auto;
    height: 52px;
    border-radius: 16px;
    border: 0;
    background: var(--accent);
    color: var(--accent-text);
    font-size: 15px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    box-shadow: 0 10px 28px rgba(0,0,0,0.32);
    transition: transform .15s ease, opacity .15s ease;
    z-index: 20;
  }
  .fab:active { transform: scale(0.97); }

  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(4px);
    display: none;
    align-items: flex-end;
    justify-content: center;
    z-index: 50;
  }
  .backdrop.open { display: flex; }

  .sheet {
    width: 100%;
    max-width: 600px;
    background: var(--surface);
    border-top-left-radius: 24px;
    border-top-right-radius: 24px;
    border-top: 1px solid var(--sep);
    padding: 18px 16px max(20px, env(safe-area-inset-bottom));
    animation: slideUp .22s cubic-bezier(.22,1,.36,1);
  }
  @keyframes slideUp {
    from { transform: translateY(40px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  .sheet-hd {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }
  .sheet-hd h3 { margin: 0; font-size: 18px; font-weight: 800; }

  .field-lbl {
    font-size: 12px;
    font-weight: 700;
    color: var(--hint);
    margin: 0 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  textarea {
    width: 100%;
    min-height: 92px;
    resize: none;
    border-radius: 14px;
    border: 1px solid var(--sep);
    background: var(--bg);
    color: var(--text);
    font: inherit;
    font-size: 15px;
    padding: 12px;
    outline: none;
    margin-bottom: 14px;
  }
  textarea:focus { border-color: var(--accent); }

  .prio-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }
  .prio-opt {
    border: 2px solid var(--sep);
    background: var(--card);
    color: var(--text);
    border-radius: 12px;
    padding: 10px 6px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    text-align: center;
    transition: all .15s ease;
  }
  .prio-opt.sel.N { border-color: var(--norm); background: var(--norm-bg); color: var(--norm); }
  .prio-opt.sel.H { border-color: var(--high); background: var(--high-bg); color: var(--high); }
  .prio-opt.sel.C { border-color: var(--crit); background: var(--crit-bg); color: var(--crit); }

  .submit-btn {
    width: 100%;
    height: 48px;
    border: 0;
    border-radius: 14px;
    background: var(--accent);
    color: var(--accent-text);
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }
  .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .toast {
    position: fixed;
    top: 14px;
    left: 50%;
    transform: translateX(-50%) translateY(-80px);
    background: #111827;
    color: #fff;
    padding: 10px 16px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    transition: transform .25s cubic-bezier(.22,1,.36,1);
    z-index: 80;
    white-space: nowrap;
  }
  .toast.show { transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>

<div class="toast" id="toast"></div>

<section class="hero">
  <div class="hero-top">
    <div>
      <div class="loc-pill" id="locPill">📍 ...</div>
      <h1 class="title" id="pageTitle">Задачи</h1>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <a class="icon-btn" id="toKassaLink" href="/webapp/kassa" style="width:auto;padding:0 11px;font-size:12px;font-weight:700;text-decoration:none;">💳 Касса</a>
      <button class="icon-btn" id="refreshBtn" type="button" title="Refresh">↻</button>
    </div>
  </div>

  <div class="prog-row">
    <span id="progLabel">Выполнено за сессию</span>
    <strong id="progVal">0 / 0</strong>
  </div>
  <div class="prog-track"><div class="prog-fill" id="progFill"></div></div>

  <div class="stats">
    <div class="stat c" data-f="C"><span class="dot"></span><span class="lbl">Critical</span><span class="num" id="sC">0</span></div>
    <div class="stat h" data-f="H"><span class="dot"></span><span class="lbl">High</span><span class="num" id="sH">0</span></div>
    <div class="stat n" data-f="N"><span class="dot"></span><span class="lbl">Normal</span><span class="num" id="sN">0</span></div>
  </div>
</section>

<nav class="tabs" id="tabs">
  <button class="tab active" data-f="A" type="button"><span id="tAll">Все</span> <span class="cnt" id="cA">0</span></button>
  <button class="tab tc" data-f="C" type="button">🔴 Critical <span class="cnt" id="cC">0</span></button>
  <button class="tab th" data-f="H" type="button">🟠 High <span class="cnt" id="cH">0</span></button>
  <button class="tab tn" data-f="N" type="button">🟢 Normal <span class="cnt" id="cN">0</span></button>
</nav>

<main class="list" id="list"></main>

<button class="fab" id="openAddBtn" type="button">＋ <span id="fabText">Новая задача</span></button>

<div class="backdrop" id="modal">
  <div class="sheet">
    <div class="sheet-hd">
      <h3 id="modalTitle">Новая задача</h3>
      <button class="icon-btn" id="closeModalBtn" type="button">✕</button>
    </div>
    <div class="field-lbl" id="lblDesc">Описание</div>
    <textarea id="taskInput" placeholder="Опишите задачу..."></textarea>
    <div class="field-lbl" id="lblPrio">Критичность</div>
    <div class="prio-grid" id="prioGrid">
      <button class="prio-opt sel N" data-p="N" type="button">🟢 Normal</button>
      <button class="prio-opt H" data-p="H" type="button">🟠 High</button>
      <button class="prio-opt C" data-p="C" type="button">🔴 Critical</button>
    </div>
    <button class="submit-btn" id="submitTaskBtn" type="button">Добавить задачу</button>
  </div>
</div>

<script>
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const urlParams = new URLSearchParams(window.location.search);
const forcedLoc = urlParams.get("loc") || "";

const I18N = {
  ru: {
    title: "Задачи",
    all: "Все",
    prog: "Выполнено за сессию",
    addBtn: "Новая задача",
    modalTitle: "Новая задача",
    desc: "Описание",
    descPh: "Опишите задачу...",
    prio: "Критичность",
    create: "Добавить задачу",
    creating: "Сохранение...",
    emptyTitle: "Все задачи выполнены!",
    emptySub: "Нажмите «Новая задача», чтобы добавить первую.",
    emptyFltTitle: "Пусто в этой категории",
    emptyFltSub: "Нет задач с выбранной критичностью.",
    doneToast: "выполнено ✓",
    addedToast: "Задача добавлена ✓",
    errAuth: "Откройте доску через кнопку в Telegram-боте.",
    errNet: "Ошибка соединения. Попробуйте ещё раз.",
    tapPrioHint: "Нажмите на бейдж, чтобы сменить критичность"
  },
  hy: {
    title: "Առաջադրանքներ",
    all: "Բոլորը",
    prog: "Կատարված է այս սեսիայում",
    addBtn: "Նոր առաջադրանք",
    modalTitle: "Նոր առաջադրանք",
    desc: "Նկարագրություն",
    descPh: "Գրեք առաջադրանքի նկարագրությունը...",
    prio: "Կարևորություն",
    create: "Ավելացնել առաջադրանք",
    creating: "Պահպանում...",
    emptyTitle: "Բոլոր առաջադրանքները կատարված են",
    emptySub: "Սեղմեք «Նոր առաջադրանք»՝ նորը ավելացնելու համար։",
    emptyFltTitle: "Այս բաժինը դատարկ է",
    emptyFltSub: "Ընտրված կարևորությամբ առաջադրանքներ չկան։",
    doneToast: "կատարված է ✓",
    addedToast: "Առաջադրանքը ավելացվեց ✓",
    errAuth: "Բացեք տախտակը Telegram բոտի կոճակից։",
    errNet: "Կապի սխալ։ Փորձեք կրկին։",
    tapPrioHint: "Սեղմեք՝ կարևորությունը փոխելու համար"
  }
};

const PRIO_LABELS = { C: "🔴 Critical", H: "🟠 High", N: "🟢 Normal" };
const PRIO_NEXT = { N: "H", H: "C", C: "N" };

let state = {
  lang: "ru",
  locCode: forcedLoc || "GN",
  locName: "...",
  tasks: [],
  filter: "A",
  sessionDone: 0,
  sessionTotal: 0,
  newPrio: "N"
};

function t(k) { return (I18N[state.lang] || I18N.ru)[k] || k; }

function haptic(type) {
  try {
    if (!tg || !tg.HapticFeedback) return;
    if (type === "success") tg.HapticFeedback.notificationOccurred("success");
    else if (type === "error") tg.HapticFeedback.notificationOccurred("error");
    else tg.HapticFeedback.impactOccurred("light");
  } catch (e) {}
}

let toastTimer = null;
function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2000);
}

async function apiFetch(path, opts = {}) {
  const initData = tg ? tg.initData : "";
  const headers = Object.assign(
    { "Content-Type": "application/json", "X-Telegram-Init-Data": initData },
    opts.headers || {}
  );
  const res = await fetch(path, Object.assign({}, opts, { headers }));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "API error");
  return data;
}

function applyLang() {
  document.getElementById("pageTitle").textContent = t("title");
  document.getElementById("tAll").textContent = t("all");
  document.getElementById("progLabel").textContent = t("prog");
  document.getElementById("fabText").textContent = t("addBtn");
  document.getElementById("modalTitle").textContent = t("modalTitle");
  document.getElementById("lblDesc").textContent = t("desc");
  document.getElementById("taskInput").placeholder = t("descPh");
  document.getElementById("lblPrio").textContent = t("prio");
  document.getElementById("submitTaskBtn").textContent = t("create");
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function render() {
  applyLang();
  document.getElementById("locPill").textContent = "📍 " + state.locName;

  const counts = { C: 0, H: 0, N: 0 };
  for (const item of state.tasks) {
    const p = item.priority || "N";
    counts[p] = (counts[p] || 0) + 1;
  }
  const active = state.tasks.length;
  if (state.sessionTotal < active + state.sessionDone) {
    state.sessionTotal = active + state.sessionDone;
  }

  document.getElementById("sC").textContent = counts.C;
  document.getElementById("sH").textContent = counts.H;
  document.getElementById("sN").textContent = counts.N;
  document.getElementById("cA").textContent = active;
  document.getElementById("cC").textContent = counts.C;
  document.getElementById("cH").textContent = counts.H;
  document.getElementById("cN").textContent = counts.N;

  const denom = Math.max(1, state.sessionTotal);
  const doneVal = state.sessionTotal === 0 ? 0 : Math.max(state.sessionDone, state.sessionTotal - active);
  const pct = state.sessionTotal === 0 ? 100 : Math.round((doneVal / denom) * 100);
  document.getElementById("progVal").textContent = `${doneVal} / ${state.sessionTotal}`;
  document.getElementById("progFill").style.width = `${pct}%`;

  document.querySelectorAll(".tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.f === state.filter);
  });

  const shown = state.filter === "A"
    ? state.tasks
    : state.tasks.filter(x => (x.priority || "N") === state.filter);

  const listEl = document.getElementById("list");
  if (shown.length === 0) {
    const isFiltered = state.filter !== "A" && active > 0;
    listEl.innerHTML = `
      <div class="empty">
        <div class="em">${isFiltered ? "🔎" : "🎉"}</div>
        <div class="et">${isFiltered ? t("emptyFltTitle") : t("emptyTitle")}</div>
        <div class="es">${isFiltered ? t("emptyFltSub") : t("emptySub")}</div>
      </div>`;
    return;
  }

  listEl.innerHTML = shown.map(item => {
    const p = item.priority || "N";
    return `
      <article class="card p${p}" data-id="${item.id}">
        <button class="chk" type="button" data-act="done" data-id="${item.id}" aria-label="Complete"></button>
        <div class="card-body">
          <div class="card-meta">
            <span class="tid">#${item.id}</span>
            <button class="p-pill ${p}" type="button" data-act="prio" data-id="${item.id}" data-p="${p}" title="${t("tapPrioHint")}">${PRIO_LABELS[p] || PRIO_LABELS.N}</button>
          </div>
          <div class="desc">${escapeHtml(item.description)}</div>
        </div>
      </article>`;
  }).join("");
}

async function loadTasks(showSpin = true) {
  const btn = document.getElementById("refreshBtn");
  if (showSpin) btn.classList.add("spin");
  try {
    const qs = forcedLoc ? `?loc=${encodeURIComponent(forcedLoc)}` : "";
    const data = await apiFetch("/api/webapp/tasks" + qs);
    state.lang = data.lang || "ru";
    state.locCode = data.location_code || state.locCode;
    state.locName = data.location_name || state.locCode;
    state.tasks = data.tasks || [];
    const kLink = document.getElementById("toKassaLink");
    if (kLink) {
      kLink.href = `/webapp/kassa?loc=${encodeURIComponent(state.locCode)}`;
      kLink.textContent = state.lang === "hy" ? "💳 Դրամարկղ" : "💳 Касса";
    }
    if (state.sessionTotal === 0) state.sessionTotal = state.tasks.length;
    render();
  } catch (e) {
    haptic("error");
    document.getElementById("list").innerHTML = `
      <div class="empty">
        <div class="em">🔒</div>
        <div class="et">${t("errAuth")}</div>
        <div class="es">${escapeHtml(e.message)}</div>
      </div>`;
  } finally {
    btn.classList.remove("spin");
  }
}

async function completeTask(id) {
  const card = document.querySelector(`.card[data-id="${id}"]`);
  if (card) {
    card.classList.add("completing");
    const chk = card.querySelector(".chk");
    if (chk) chk.textContent = "✓";
  }
  haptic("success");
  try {
    const data = await apiFetch(`/api/webapp/tasks/${id}/complete`, {
      method: "POST",
      body: JSON.stringify({ location: state.locCode })
    });
    state.sessionDone += 1;
    state.tasks = data.tasks || state.tasks.filter(x => x.id !== id);
    showToast(`#${id} ${t("doneToast")}`);
    setTimeout(render, 180);
  } catch (e) {
    if (card) card.classList.remove("completing");
    haptic("error");
    showToast(t("errNet"));
  }
}

async function cyclePriority(id, curPrio) {
  const nextP = PRIO_NEXT[curPrio] || "N";
  haptic("light");
  try {
    const data = await apiFetch(`/api/webapp/tasks/${id}/priority`, {
      method: "PATCH",
      body: JSON.stringify({ priority: nextP, location: state.locCode })
    });
    state.tasks = data.tasks || state.tasks;
    showToast(`${PRIO_LABELS[nextP]}`);
    render();
  } catch (e) {
    haptic("error");
    showToast(t("errNet"));
  }
}

document.getElementById("list").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-act]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  if (btn.dataset.act === "done") completeTask(id);
  else if (btn.dataset.act === "prio") cyclePriority(id, btn.dataset.p || "N");
});

document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  haptic("light");
  state.filter = btn.dataset.f;
  render();
});

document.querySelectorAll(".stat").forEach(el => {
  el.addEventListener("click", () => {
    haptic("light");
    const f = el.dataset.f;
    state.filter = (state.filter === f) ? "A" : f;
    render();
  });
});

document.getElementById("refreshBtn").addEventListener("click", () => {
  haptic("light");
  loadTasks(true);
});

const modal = document.getElementById("modal");
const taskInput = document.getElementById("taskInput");

function openModal() {
  haptic("light");
  modal.classList.add("open");
  setTimeout(() => taskInput.focus(), 100);
}
function closeModal() {
  modal.classList.remove("open");
}

document.getElementById("openAddBtn").addEventListener("click", openModal);
document.getElementById("closeModalBtn").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

document.getElementById("prioGrid").addEventListener("click", (e) => {
  const btn = e.target.closest(".prio-opt");
  if (!btn) return;
  haptic("light");
  state.newPrio = btn.dataset.p;
  document.querySelectorAll(".prio-opt").forEach(b => b.classList.toggle("sel", b.dataset.p === state.newPrio));
});

document.getElementById("submitTaskBtn").addEventListener("click", async () => {
  const desc = taskInput.value.trim();
  if (!desc) { haptic("error"); taskInput.focus(); return; }
  const submitBtn = document.getElementById("submitTaskBtn");
  submitBtn.disabled = true;
  submitBtn.textContent = t("creating");
  try {
    const data = await apiFetch("/api/webapp/tasks", {
      method: "POST",
      body: JSON.stringify({
        description: desc,
        priority: state.newPrio,
        location: state.locCode
      })
    });
    state.tasks = data.tasks || state.tasks;
    state.sessionTotal += 1;
    taskInput.value = "";
    state.newPrio = "N";
    document.querySelectorAll(".prio-opt").forEach(b => b.classList.toggle("sel", b.dataset.p === "N"));
    closeModal();
    haptic("success");
    showToast(t("addedToast"));
    render();
  } catch (e) {
    haptic("error");
    showToast(t("errNet"));
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = t("create");
  }
});

loadTasks(false);
</script>
</body>
</html>
"""
