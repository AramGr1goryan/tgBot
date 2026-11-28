# api/kassa_webapp.py
# Telegram Mini App (WebApp) for RobixLab Kassa: Payments, Expenses (/rc), Cash Reconciliation (/check), Undo (/undo)

KASSA_WEBAPP_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>RobixLab Касса</title>
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
    --ok: #22c55e;
    --ok-bg: rgba(34, 197, 94, 0.14);
    --warn: #f59e0b;
    --warn-bg: rgba(245, 158, 11, 0.15);
    --err: #ef4444;
    --err-bg: rgba(239, 68, 68, 0.14);
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
    padding: 14px 14px 40px;
    max-width: 600px;
    margin: 0 auto;
  }

  /* Header */
  .hero {
    background: var(--surface);
    border: 1px solid var(--sep);
    border-radius: 20px;
    padding: 15px 16px;
    margin-bottom: 12px;
  }
  .hero-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 4px;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.14);
    color: var(--accent);
  }
  .pill.exec {
    background: var(--ok-bg);
    color: var(--ok);
  }
  .title {
    margin: 2px 0 0;
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .switch-btn {
    border: 1px solid var(--sep);
    background: var(--card);
    color: var(--text);
    border-radius: 12px;
    padding: 8px 11px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
    white-space: nowrap;
  }

  /* Nav Tabs */
  .tabs {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    background: var(--surface);
    border: 1px solid var(--sep);
    padding: 5px;
    border-radius: 16px;
    margin-bottom: 14px;
  }
  .tab {
    border: 0;
    background: transparent;
    color: var(--hint);
    font-size: 13px;
    font-weight: 700;
    padding: 10px 6px;
    border-radius: 12px;
    cursor: pointer;
    transition: all .16s ease;
  }
  .tab.active {
    background: var(--accent);
    color: var(--accent-text);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  }

  .panel { display: none; }
  .panel.active { display: block; }

  .box {
    background: var(--surface);
    border: 1px solid var(--sep);
    border-radius: 18px;
    padding: 15px;
    margin-bottom: 12px;
  }
  .lbl {
    font-size: 11px;
    font-weight: 700;
    color: var(--hint);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .inp-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }
  input[type="text"], input[type="number"] {
    width: 100%;
    height: 46px;
    border-radius: 13px;
    border: 1px solid var(--sep);
    background: var(--bg);
    color: var(--text);
    font: inherit;
    font-size: 15px;
    font-weight: 600;
    padding: 0 38px 0 13px;
    outline: none;
    transition: border-color .15s ease;
  }
  input:focus { border-color: var(--accent); }

  .clear-btn {
    position: absolute;
    right: 8px;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: 0;
    background: var(--card);
    color: var(--hint);
    font-size: 13px;
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
  }
  .clear-btn.show { display: inline-flex; }

  /* Search results */
  .results {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 240px;
    overflow-y: auto;
  }
  .c-item {
    border: 1px solid var(--sep);
    background: var(--card);
    border-radius: 13px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    cursor: pointer;
    text-align: left;
    color: var(--text);
    transition: border-color .15s ease, transform .12s ease;
  }
  .c-item:active { transform: scale(0.98); }
  .c-item.sel {
    border-color: var(--accent);
    background: rgba(59, 130, 246, 0.14);
  }
  .c-main { min-width: 0; flex: 1; }
  .c-name { font-size: 14px; font-weight: 700; word-break: break-word; }
  .c-sub { font-size: 11px; color: var(--hint); margin-top: 2px; }
  .c-tag {
    font-size: 10px;
    font-weight: 800;
    padding: 3px 7px;
    border-radius: 999px;
    flex-shrink: 0;
  }
  .c-tag.ok { background: var(--ok-bg); color: var(--ok); }
  .c-tag.warn { background: var(--warn-bg); color: var(--warn); }

  .pref-notice {
    margin-top: 8px;
    padding: 9px 11px;
    border-radius: 11px;
    background: var(--warn-bg);
    color: var(--warn);
    font-size: 12px;
    font-weight: 600;
    display: none;
  }
  .pref-notice.show { display: block; }

  /* Amount presets */
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 9px;
  }
  .chip {
    border: 1px solid var(--sep);
    background: var(--card);
    color: var(--text);
    border-radius: 999px;
    padding: 6px 11px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all .14s ease;
  }
  .chip:active { transform: scale(0.94); }
  .chip.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-text);
  }

  /* Payment methods */
  .methods {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .m-btn {
    border: 2px solid var(--sep);
    background: var(--card);
    color: var(--text);
    border-radius: 14px;
    padding: 12px 10px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: all .15s ease;
  }
  .m-btn.sel.n { border-color: var(--ok); background: var(--ok-bg); color: var(--ok); }
  .m-btn.sel.bn { border-color: var(--accent); background: rgba(59,130,246,0.15); color: var(--accent); }

  .primary-btn {
    width: 100%;
    height: 50px;
    border: 0;
    border-radius: 15px;
    background: var(--accent);
    color: var(--accent-text);
    font-size: 15px;
    font-weight: 800;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: transform .14s ease, opacity .14s ease;
  }
  .primary-btn:active { transform: scale(0.98); }
  .primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .danger-btn {
    width: 100%;
    height: 44px;
    border: 1px solid rgba(239,68,68,0.35);
    border-radius: 13px;
    background: var(--err-bg);
    color: var(--err);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    margin-top: 10px;
  }

  .status-banner {
    border-radius: 15px;
    padding: 13px 14px;
    margin-top: 12px;
    font-size: 13px;
    line-height: 1.45;
    display: none;
  }
  .status-banner.show { display: block; }
  .status-banner.ok { background: var(--ok-bg); border: 1px solid rgba(34,197,94,0.35); color: var(--text); }
  .status-banner.err { background: var(--err-bg); border: 1px solid rgba(239,68,68,0.35); color: var(--text); }

  .dds-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    border-radius: 14px;
    background: var(--card);
    border: 1px solid var(--sep);
    margin-bottom: 12px;
  }
  .dds-val { font-size: 18px; font-weight: 800; color: var(--accent); }

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
      <div class="badges">
        <span class="pill" id="locPill">📍 ...</span>
        <span class="pill exec" id="execPill">👤 ...</span>
      </div>
      <h1 class="title" id="pageTitle">Касса и Платежи</h1>
    </div>
    <a class="switch-btn" id="toTasksLink" href="/webapp/tasks">📋 <span id="toTasksText">Задачи</span></a>
  </div>
</section>

<nav class="tabs" id="tabs">
  <button class="tab active" data-t="pay" type="button" id="tabPay">💳 Оплата</button>
  <button class="tab" data-t="rc" type="button" id="tabRc">💸 Расход</button>
  <button class="tab" data-t="check" type="button" id="tabCheck">📊 Сверка</button>
</nav>

<!-- TAB 1: PAYMENT -->
<section class="panel active" id="panel-pay">
  <div class="box">
    <div class="lbl">
      <span id="lblStudent">1. Ученик (Alfa CRM)</span>
      <span id="searchStatus"></span>
    </div>
    <div class="inp-wrap">
      <input type="text" id="studentQuery" placeholder="Имя, фамилия или CRM ID..." autocomplete="off">
      <button class="clear-btn" id="clearStudentBtn" type="button">✕</button>
    </div>
    <div class="results" id="studentResults"></div>
    <div class="pref-notice" id="prefNotice"></div>
  </div>

  <div class="box">
    <div class="lbl"><span id="lblAmount">2. Сумма (AMD)</span></div>
    <input type="number" id="payAmount" inputmode="numeric" placeholder="Например: 50000">
    <div class="chips" id="payChips">
      <button class="chip" data-v="2000" type="button">2 000</button>
      <button class="chip" data-v="25000" type="button">25 000</button>
      <button class="chip" data-v="30000" type="button">30 000</button>
      <button class="chip" data-v="40000" type="button">40 000</button>
      <button class="chip" data-v="50000" type="button">50 000</button>
    </div>
  </div>

  <div class="box">
    <div class="lbl"><span id="lblMethod">3. Способ оплаты</span></div>
    <div class="methods" id="methodGrid">
      <button class="m-btn sel n" data-m="n" type="button">💵 <span id="mCash">Наличные (n)</span></button>
      <button class="m-btn bn" data-m="b.n" type="button">💳 <span id="mTerm">Терминал (b.n)</span></button>
    </div>
  </div>

  <button class="primary-btn" id="submitPayBtn" type="button">✅ <span id="btnPayText">Провести оплату</span></button>
  <div class="status-banner" id="payResult"></div>

  <div class="box" id="lastPayBox" style="display:none;margin-top:14px;">
    <div class="lbl"><span id="lblLastPay">Последний платёж</span></div>
    <div id="lastPayInfo" style="font-size:14px;font-weight:700;"></div>
    <button class="danger-btn" id="undoPayBtn" type="button">🗑 <span id="btnUndoText">Отменить последний платёж</span></button>
  </div>
</section>

<!-- TAB 2: EXPENSE (/rc) -->
<section class="panel" id="panel-rc">
  <div class="box">
    <div class="lbl"><span id="lblRcAmount">Сумма расхода (AMD)</span></div>
    <input type="number" id="rcAmount" inputmode="numeric" placeholder="Например: 5000">
    <div class="chips" id="rcChips">
      <button class="chip" data-v="1000" type="button">1 000</button>
      <button class="chip" data-v="2000" type="button">2 000</button>
      <button class="chip" data-v="5000" type="button">5 000</button>
      <button class="chip" data-v="10000" type="button">10 000</button>
      <button class="chip" data-v="20000" type="button">20 000</button>
    </div>
  </div>

  <div class="box">
    <div class="lbl"><span id="lblRcReason">Причина расхода</span></div>
    <input type="text" id="rcReason" placeholder="Например: Хозтовары, вода, маркеры...">
  </div>

  <button class="primary-btn" id="submitRcBtn" type="button">💸 <span id="btnRcText">Записать расход в ДДС</span></button>
  <div class="status-banner" id="rcResult"></div>
</section>

<!-- TAB 3: CHECK KASSA (/check) -->
<section class="panel" id="panel-check">
  <div class="box">
    <div class="dds-card">
      <div>
        <div class="lbl" style="margin-bottom:2px;"><span id="lblDdsCur">Текущее сальдо по ДДС</span></div>
        <div class="dds-val" id="ddsVal">— AMD</div>
      </div>
      <button class="switch-btn" id="loadDdsBtn" type="button">↻ <span id="btnLoadDds">Показать</span></button>
    </div>

    <div class="lbl"><span id="lblCheckAmount">Фактическая сумма в кассе (AMD)</span></div>
    <input type="number" id="checkAmount" inputmode="numeric" placeholder="Введите сумму наличных в кассе...">
  </div>

  <button class="primary-btn" id="submitCheckBtn" type="button">📊 <span id="btnCheckText">Сверить кассу и отправить отчёт</span></button>
  <div class="status-banner" id="checkResult"></div>
</section>

<script>
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const urlParams = new URLSearchParams(window.location.search);
const forcedLoc = urlParams.get("loc") || "";
const initTab = urlParams.get("tab") || "pay";

const I18N = {
  ru: {
    title: "Касса и Платежи",
    tasks: "Задачи",
    tabPay: "💳 Оплата",
    tabRc: "💸 Расход",
    tabCheck: "📊 Сверка",
    lblStudent: "1. Ученик (Alfa CRM)",
    studentPh: "Имя, фамилия или CRM ID...",
    searching: "Поиск...",
    noStudents: "Клиенты не найдены",
    lblAmount: "2. Сумма (AMD)",
    lblMethod: "3. Способ оплаты",
    mCash: "Наличные (n)",
    mTerm: "Терминал (b.n)",
    btnPay: "Провести оплату",
    paying: "Проводим в CRM и ДДС...",
    lblLastPay: "Последний платёж",
    btnUndo: "Отменить последний платёж",
    undoing: "Отменяем платёж...",
    lblRcAmount: "Сумма расхода (AMD)",
    lblRcReason: "Причина расхода",
    rcReasonPh: "Например: Вода, канцтовары...",
    btnRc: "Записать расход в ДДС",
    savingRc: "Записываем в ДДС...",
    lblDdsCur: "Текущее сальдо по ДДС",
    btnLoadDds: "Узнать",
    lblCheckAmount: "Фактическая сумма в кассе (AMD)",
    checkPh: "Введите сумму в кассе...",
    btnCheck: "Сверить кассу и отправить отчёт",
    checking: "Сверяем с таблицей ДДС...",
    prefWarn: "У ученика нет префикса филиала — при оплате автоматически добавится",
    selectStudentErr: "Сначала выберите ученика из списка поиска",
    enterAmountErr: "Введите корректную сумму",
    enterReasonErr: "Укажите причину расхода",
    unregErr: "Сначала зарегистрируйте имя в боте командой /start",
  },
  hy: {
    title: "Դրամարկղ և Վճարումներ",
    tasks: "Առաջադրանքներ",
    tabPay: "💳 Վճարում",
    tabRc: "💸 Ծախս",
    tabCheck: "📊 Ստուգում",
    lblStudent: "1. Աշակերտ (Alfa CRM)",
    studentPh: "Անուն, ազգանուն կամ CRM ID...",
    searching: "Որոնում...",
    noStudents: "Աշակերտներ չեն գտնվել",
    lblAmount: "2. Գումար (AMD)",
    lblMethod: "3. Վճարման եղանակ",
    mCash: "Կանխիկ (n)",
    mTerm: "Տերմինալ (b.n)",
    btnPay: "Գրանցել վճարումը",
    paying: "Գրանցվում է CRM և ԴԴՍ...",
    lblLastPay: "Վերջին վճարումը",
    btnUndo: "Չեղարկել վերջին վճարումը",
    undoing: "Չեղարկվում է...",
    lblRcAmount: "Ծախսի գումար (AMD)",
    lblRcReason: "Ծախսի պատճառ",
    rcReasonPh: "Օրինակ՝ Ջուր, գրենական պիտույքներ...",
    btnRc: "Գրանցել ծախսը ԴԴՍ-ում",
    savingRc: "Գրանցվում է ԴԴՍ-ում...",
    lblDdsCur: "ԴԴՍ ընթացիկ մնացորդ",
    btnLoadDds: "Ցույց տալ",
    lblCheckAmount: "Փաստացի գումարը դրամարկղում (AMD)",
    checkPh: "Մուտքագրեք գումարը...",
    btnCheck: "Ստուգել դրամարկղը և ուղարկել",
    checking: "Ստուգվում է ԴԴՍ-ի հետ...",
    prefWarn: "Աշակերտը չունի մասնաճյուղի պրեֆիքս — վճարելիս ավտոմատ կավելացվի",
    selectStudentErr: "Նախ ընտրեք աշակերտին որոնման ցանկից",
    enterAmountErr: "Մուտքագրեք ճիշտ գումար",
    enterReasonErr: "Նշեք ծախսի պատճառը",
    unregErr: "Նախ գրանցեք ձեր անունը բոտում՝ /start հրամանով",
  }
};

let state = {
  lang: "ru",
  locCode: forcedLoc || "GN",
  locName: "...",
  crmPrefix: "G.N",
  executorName: "...",
  isRegistered: true,
  tab: ["pay", "rc", "check"].includes(initTab) ? initTab : "pay",
  selectedStudent: null,
  candidates: [],
  method: "n",
  lastPayment: null,
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
  toastTimer = setTimeout(() => el.classList.remove("show"), 2300);
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtAmd(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toLocaleString("ru-RU") + " AMD";
}

async function apiFetch(path, opts = {}) {
  const initData = tg ? tg.initData : "";
  const headers = Object.assign(
    { "Content-Type": "application/json", "X-Telegram-Init-Data": initData },
    opts.headers || {}
  );
  const res = await fetch(path, Object.assign({}, opts, { headers }));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Ошибка запроса");
  return data;
}

function applyLang() {
  document.getElementById("pageTitle").textContent = t("title");
  document.getElementById("toTasksText").textContent = t("tasks");
  document.getElementById("tabPay").textContent = t("tabPay");
  document.getElementById("tabRc").textContent = t("tabRc");
  document.getElementById("tabCheck").textContent = t("tabCheck");
  document.getElementById("lblStudent").textContent = t("lblStudent");
  document.getElementById("studentQuery").placeholder = t("studentPh");
  document.getElementById("lblAmount").textContent = t("lblAmount");
  document.getElementById("lblMethod").textContent = t("lblMethod");
  document.getElementById("mCash").textContent = t("mCash");
  document.getElementById("mTerm").textContent = t("mTerm");
  document.getElementById("btnPayText").textContent = t("btnPay");
  document.getElementById("lblLastPay").textContent = t("lblLastPay");
  document.getElementById("btnUndoText").textContent = t("btnUndo");
  document.getElementById("lblRcAmount").textContent = t("lblRcAmount");
  document.getElementById("lblRcReason").textContent = t("lblRcReason");
  document.getElementById("rcReason").placeholder = t("rcReasonPh");
  document.getElementById("btnRcText").textContent = t("btnRc");
  document.getElementById("lblDdsCur").textContent = t("lblDdsCur");
  document.getElementById("btnLoadDds").textContent = t("btnLoadDds");
  document.getElementById("lblCheckAmount").textContent = t("lblCheckAmount");
  document.getElementById("checkAmount").placeholder = t("checkPh");
  document.getElementById("btnCheckText").textContent = t("btnCheck");
}

function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.t === tab));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === `panel-${tab}`));
}

function renderLastPayment() {
  const box = document.getElementById("lastPayBox");
  const info = document.getElementById("lastPayInfo");
  if (state.lastPayment && state.lastPayment.pay_id) {
    box.style.display = "block";
    info.textContent = `${state.lastPayment.name} · ${fmtAmd(state.lastPayment.amount)}`;
  } else {
    box.style.display = "none";
  }
}

function renderCandidates() {
  const box = document.getElementById("studentResults");
  const notice = document.getElementById("prefNotice");

  if (state.selectedStudent) {
    const c = state.selectedStudent;
    const tagCls = c.has_prefix ? "ok" : "warn";
    const tagTxt = c.has_prefix ? `✓ ${state.crmPrefix}` : `+ ${state.crmPrefix}`;
    box.innerHTML = `
      <div class="c-item sel" data-id="${c.id}">
        <div class="c-main">
          <div class="c-name">✅ ${escapeHtml(c.name)}</div>
          <div class="c-sub">ID: ${c.id}${c.phones ? " · " + escapeHtml(c.phones) : ""}</div>
        </div>
        <span class="c-tag ${tagCls}">${escapeHtml(tagTxt)}</span>
      </div>`;
    if (!c.has_prefix) {
      notice.textContent = `⚠️ ${t("prefWarn")} «${state.crmPrefix} |»`;
      notice.classList.add("show");
    } else {
      notice.classList.remove("show");
    }
    return;
  }

  notice.classList.remove("show");
  if (!state.candidates.length) {
    box.innerHTML = "";
    return;
  }

  box.innerHTML = state.candidates.map(c => {
    const tagCls = c.has_prefix ? "ok" : "warn";
    const tagTxt = c.has_prefix ? `✓ ${state.crmPrefix}` : `без ${state.crmPrefix}`;
    return `
      <button class="c-item" type="button" data-id="${c.id}">
        <div class="c-main">
          <div class="c-name">${escapeHtml(c.name)}</div>
          <div class="c-sub">ID: ${c.id}${c.phones ? " · " + escapeHtml(c.phones) : ""}</div>
        </div>
        <span class="c-tag ${tagCls}">${escapeHtml(tagTxt)}</span>
      </button>`;
  }).join("");
}

async function initKassa() {
  switchTab(state.tab);
  try {
    const qs = forcedLoc ? `?loc=${encodeURIComponent(forcedLoc)}` : "";
    const data = await apiFetch("/api/webapp/kassa/state" + qs);
    state.lang = data.lang || "ru";
    state.locCode = data.location_code || state.locCode;
    state.locName = data.location_name || state.locCode;
    state.crmPrefix = data.crm_prefix || "G.N";
    state.executorName = data.executor_name || "—";
    state.isRegistered = Boolean(data.is_registered);
    state.lastPayment = data.last_payment || null;

    applyLang();
    document.getElementById("locPill").textContent = "📍 " + state.locName;
    document.getElementById("execPill").textContent = "👤 " + state.executorName;
    document.getElementById("toTasksLink").href = `/webapp/tasks?loc=${encodeURIComponent(state.locCode)}`;
    renderLastPayment();
  } catch (e) {
    showToast(e.message);
  }
}

// Tabs
document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  haptic("light");
  switchTab(btn.dataset.t);
});

// Live student search
let searchTimer = null;
const studentInput = document.getElementById("studentQuery");
const clearBtn = document.getElementById("clearStudentBtn");

studentInput.addEventListener("input", () => {
  const q = studentInput.value.trim();
  clearBtn.classList.toggle("show", q.length > 0);
  state.selectedStudent = null;
  clearTimeout(searchTimer);
  if (q.length < 2) {
    state.candidates = [];
    document.getElementById("searchStatus").textContent = "";
    renderCandidates();
    return;
  }
  document.getElementById("searchStatus").textContent = t("searching");
  searchTimer = setTimeout(async () => {
    try {
      const data = await apiFetch(`/api/webapp/kassa/customers?q=${encodeURIComponent(q)}&loc=${encodeURIComponent(state.locCode)}`);
      state.candidates = data.customers || [];
      document.getElementById("searchStatus").textContent = state.candidates.length ? `(${state.candidates.length})` : t("noStudents");
      if (state.candidates.length === 1) {
        state.selectedStudent = state.candidates[0];
      }
      renderCandidates();
    } catch (e) {
      document.getElementById("searchStatus").textContent = "";
    }
  }, 320);
});

clearBtn.addEventListener("click", () => {
  haptic("light");
  studentInput.value = "";
  clearBtn.classList.remove("show");
  state.selectedStudent = null;
  state.candidates = [];
  document.getElementById("searchStatus").textContent = "";
  renderCandidates();
  studentInput.focus();
});

document.getElementById("studentResults").addEventListener("click", (e) => {
  const item = e.target.closest(".c-item");
  if (!item) return;
  const id = Number(item.dataset.id);
  const found = state.candidates.find(x => x.id === id);
  if (found) {
    haptic("light");
    state.selectedStudent = found;
    renderCandidates();
  }
});

// Amount chips
function wireChips(containerId, inputId) {
  const cont = document.getElementById(containerId);
  const inp = document.getElementById(inputId);
  cont.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    haptic("light");
    inp.value = chip.dataset.v;
    cont.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === chip));
  });
  inp.addEventListener("input", () => {
    cont.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c.dataset.v === inp.value));
  });
}
wireChips("payChips", "payAmount");
wireChips("rcChips", "rcAmount");

// Method selection
document.getElementById("methodGrid").addEventListener("click", (e) => {
  const btn = e.target.closest(".m-btn");
  if (!btn) return;
  haptic("light");
  state.method = btn.dataset.m;
  document.querySelectorAll(".m-btn").forEach(b => b.classList.toggle("sel", b === btn));
});

function showBanner(id, ok, html) {
  const el = document.getElementById(id);
  el.className = "status-banner show " + (ok ? "ok" : "err");
  el.innerHTML = html;
}

// Submit Payment
document.getElementById("submitPayBtn").addEventListener("click", async () => {
  if (!state.isRegistered) { haptic("error"); showToast(t("unregErr")); return; }
  if (!state.selectedStudent) { haptic("error"); showToast(t("selectStudentErr")); studentInput.focus(); return; }
  const amount = Number(document.getElementById("payAmount").value);
  if (!Number.isInteger(amount) || amount <= 0) { haptic("error"); showToast(t("enterAmountErr")); return; }

  const btn = document.getElementById("submitPayBtn");
  btn.disabled = true;
  document.getElementById("btnPayText").textContent = t("paying");
  try {
    const data = await apiFetch("/api/webapp/kassa/pay", {
      method: "POST",
      body: JSON.stringify({
        customer_id: state.selectedStudent.id,
        amount: amount,
        method: state.method,
        location: state.locCode,
        apply_prefix: !state.selectedStudent.has_prefix
      })
    });
    haptic("success");
    state.lastPayment = data.last_payment || null;
    renderLastPayment();
    showBanner("payResult", true, `✅ <b>${escapeHtml(data.customer_name)}</b> · <b>${fmtAmd(amount)}</b> (${escapeHtml(data.method_label)})`);
    document.getElementById("payAmount").value = "";
    document.querySelectorAll("#payChips .chip").forEach(c => c.classList.remove("active"));
  } catch (e) {
    haptic("error");
    showBanner("payResult", false, `❌ ${escapeHtml(e.message)}`);
  } finally {
    btn.disabled = false;
    document.getElementById("btnPayText").textContent = t("btnPay");
  }
});

// Undo last payment
document.getElementById("undoPayBtn").addEventListener("click", async () => {
  const btn = document.getElementById("undoPayBtn");
  btn.disabled = true;
  document.getElementById("btnUndoText").textContent = t("undoing");
  try {
    const data = await apiFetch("/api/webapp/kassa/undo", { method: "POST", body: "{}" });
    haptic("success");
    state.lastPayment = null;
    renderLastPayment();
    showBanner("payResult", true, escapeHtml(data.message));
  } catch (e) {
    haptic("error");
    showBanner("payResult", false, `❌ ${escapeHtml(e.message)}`);
  } finally {
    btn.disabled = false;
    document.getElementById("btnUndoText").textContent = t("btnUndo");
  }
});

// Submit Expense (/rc)
document.getElementById("submitRcBtn").addEventListener("click", async () => {
  if (!state.isRegistered) { haptic("error"); showToast(t("unregErr")); return; }
  const amount = Number(document.getElementById("rcAmount").value);
  const reason = document.getElementById("rcReason").value.trim();
  if (!Number.isInteger(amount) || amount <= 0) { haptic("error"); showToast(t("enterAmountErr")); return; }
  if (!reason) { haptic("error"); showToast(t("enterReasonErr")); return; }

  const btn = document.getElementById("submitRcBtn");
  btn.disabled = true;
  document.getElementById("btnRcText").textContent = t("savingRc");
  try {
    const data = await apiFetch("/api/webapp/kassa/expense", {
      method: "POST",
      body: JSON.stringify({ amount, reason, location: state.locCode })
    });
    haptic("success");
    showBanner("rcResult", true, `💸 <b>${fmtAmd(amount)}</b> — ${escapeHtml(reason)}`);
    document.getElementById("rcAmount").value = "";
    document.getElementById("rcReason").value = "";
    document.querySelectorAll("#rcChips .chip").forEach(c => c.classList.remove("active"));
  } catch (e) {
    haptic("error");
    showBanner("rcResult", false, `❌ ${escapeHtml(e.message)}`);
  } finally {
    btn.disabled = false;
    document.getElementById("btnRcText").textContent = t("btnRc");
  }
});

// Load live DDS balance
document.getElementById("loadDdsBtn").addEventListener("click", async () => {
  haptic("light");
  const el = document.getElementById("ddsVal");
  el.textContent = "...";
  try {
    const data = await apiFetch(`/api/webapp/kassa/dds?loc=${encodeURIComponent(state.locCode)}`);
    el.textContent = fmtAmd(data.dds_balance);
  } catch (e) {
    el.textContent = "Ошибка";
    showToast(e.message);
  }
});

// Submit Check Kassa (/check)
document.getElementById("submitCheckBtn").addEventListener("click", async () => {
  if (!state.isRegistered) { haptic("error"); showToast(t("unregErr")); return; }
  const rawVal = document.getElementById("checkAmount").value.trim();
  const amount = Number(rawVal);
  if (rawVal === "" || !Number.isFinite(amount)) { haptic("error"); showToast(t("enterAmountErr")); return; }

  const btn = document.getElementById("submitCheckBtn");
  btn.disabled = true;
  document.getElementById("btnCheckText").textContent = t("checking");
  try {
    const data = await apiFetch("/api/webapp/kassa/check", {
      method: "POST",
      body: JSON.stringify({ amount, location: state.locCode })
    });
    document.getElementById("ddsVal").textContent = fmtAmd(data.dds_balance);
    if (data.match) {
      haptic("success");
      showBanner("checkResult", true, `✅ <b>Суммы совпадают!</b><br>По ДДС: <b>${fmtAmd(data.dds_balance)}</b> · Факт: <b>${fmtAmd(data.actual_amount)}</b>`);
    } else {
      haptic("error");
      showBanner("checkResult", false, `❌ <b>Расхождение: ${escapeHtml(data.diff_str)} AMD</b><br>По ДДС: <b>${fmtAmd(data.dds_balance)}</b> · Факт: <b>${fmtAmd(data.actual_amount)}</b>`);
    }
  } catch (e) {
    haptic("error");
    showBanner("checkResult", false, `❌ ${escapeHtml(e.message)}`);
  } finally {
    btn.disabled = false;
    document.getElementById("btnCheckText").textContent = t("btnCheck");
  }
});

initKassa();
</script>
</body>
</html>
"""
