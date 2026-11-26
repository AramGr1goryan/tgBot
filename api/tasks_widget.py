# api/tasks_widget.py
# Telegram Bot API 10.4+ Interactive HTML Widget for /checktasks & /kchecktasks
# Rollback options:
#   1) Bot command (admin): /taskswidget off
#   2) Environment variable: TASKS_WIDGET_ENABLED=0
#   3) Git revert of this commit

import html as html_lib
import json
import os
import zlib
from typing import Any, Optional, Sequence
import httpx

MAX_HTML_RAW_BYTES = 32768
MAX_HTML_ZLIB_BYTES = 4096
MAX_CHAT_DATA_BYTES = 1024

_WIDGET_ENABLED_CACHE: Optional[bool] = None


def _env_widget_override() -> Optional[bool]:
    raw = os.getenv("TASKS_WIDGET_ENABLED")
    if raw is None or raw.strip() == "":
        return None
    val = raw.strip().lower()
    if val in ("0", "false", "no", "off", "disabled"):
        return False
    if val in ("1", "true", "yes", "on", "enabled"):
        return True
    return None


async def is_tasks_widget_enabled(pool) -> bool:
    """Return True if interactive HTML tasks widget is enabled.
    Env var TASKS_WIDGET_ENABLED takes precedence; otherwise reads bot_settings in Postgres (default True).
    """
    global _WIDGET_ENABLED_CACHE
    env_override = _env_widget_override()
    if env_override is not None:
        return env_override

    if _WIDGET_ENABLED_CACHE is not None:
        return _WIDGET_ENABLED_CACHE

    if pool is None:
        return True

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM bot_settings WHERE key = 'tasks_widget_enabled'"
            )
            if row is None:
                _WIDGET_ENABLED_CACHE = True
            else:
                _WIDGET_ENABLED_CACHE = str(row["value"]).strip().lower() not in ("0", "false", "off")
    except Exception as e:
        print(f"is_tasks_widget_enabled error: {e}")
        return True

    return _WIDGET_ENABLED_CACHE


async def set_tasks_widget_enabled(pool, enabled: bool) -> bool:
    """Persist widget feature flag in Postgres and update in-memory cache."""
    global _WIDGET_ENABLED_CACHE
    _WIDGET_ENABLED_CACHE = enabled
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_settings (key, value)
                VALUES ('tasks_widget_enabled', $1)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                "1" if enabled else "0",
            )
        return True
    except Exception as e:
        print(f"set_tasks_widget_enabled error: {e}")
        return False


def _sanitize_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).replace("\x00", "")


def build_tasks_widget_html(
    tasks: Sequence[Any],
    loc_code: str,
    loc_name: str,
    lang: str = "hy",
) -> Optional[str]:
    """Build a self-contained Telegram Bot API 10.4+ HTML widget for tasks.

    Returns the HTML string if it fits within Telegram's limits
    (<= 32,768 raw UTF-8 bytes and <= 4,096 zlib level-9 compressed bytes),
    otherwise returns None so the caller can fall back to the classic text message.
    """
    if not tasks:
        return None

    is_hy = (lang == "hy")
    title_suffix = "Առաջադրանքներ" if is_hy else "Задачи"
    all_done_text = "🎉 Բոլոր առաջադրանքները կատարված են" if is_hy else "🎉 Все задачи выполнены"
    left_label = "մնաց" if is_hy else "осталось"
    refresh_label = "↻"
    err_text = "Սխալ, փորձեք կրկին" if is_hy else "Ошибка, попробуйте снова"

    safe_loc_name = html_lib.escape(_sanitize_text(loc_name))
    safe_loc_code = _sanitize_text(loc_code)
    safe_title = f"{safe_loc_name} · {title_suffix}"

    ids = []
    rows_html = []
    for task in tasks:
        t_id = int(task["id"])
        ids.append(t_id)
        t_desc = html_lib.escape(_sanitize_text(task["description"]))
        rows_html.append(
            f'<button class="i" id="r{t_id}" type="button">'
            f'<span class="c" id="b{t_id}"></span>'
            f'<span class="m">'
            f'<span class="tag">#{t_id}</span>'
            f'<span class="tx" id="t{t_id}">{t_desc}</span>'
            f'</span>'
            f'</button>'
        )

    total = len(ids)
    ids_json = json.dumps(ids, separators=(",", ":"))
    loc_json = json.dumps(safe_loc_code)
    left_json = json.dumps(left_label, ensure_ascii=False)
    err_json = json.dumps(err_text, ensure_ascii=False)

    widget_html = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
        "*{box-sizing:border-box}"
        "body{margin:0;padding:10px 12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "color:var(--tg-theme-text-color,#111);background:transparent;font-size:14px;line-height:1.35}"
        ".hd{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}"
        ".tt{font-weight:700;font-size:15px;letter-spacing:-0.01em}"
        ".rt{display:flex;align-items:center;gap:6px;flex-shrink:0}"
        ".bd{font-size:12px;font-weight:600;padding:2px 8px;border-radius:999px;"
        "background:var(--tg-theme-secondary-bg-color,rgba(128,128,128,.14));"
        "color:var(--tg-theme-hint-color,#666)}"
        ".rf{border:0;width:26px;height:26px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:700;"
        "display:flex;align-items:center;justify-content:center;padding:0;"
        "background:var(--tg-theme-secondary-bg-color,rgba(128,128,128,.14));"
        "color:var(--tg-theme-accent-text-color,var(--tg-theme-button-color,#2481cc))}"
        ".bar{height:4px;border-radius:4px;background:var(--tg-theme-secondary-bg-color,rgba(128,128,128,.18));"
        "overflow:hidden;margin-bottom:10px}"
        ".bf{height:100%;width:0%;border-radius:4px;"
        "background:var(--tg-theme-button-color,#2481cc);transition:width .25s ease}"
        ".ls{display:flex;flex-direction:column;gap:6px}"
        ".i{display:flex;align-items:flex-start;gap:10px;width:100%;padding:8px 10px;border:0;border-radius:10px;"
        "text-align:left;font:inherit;color:inherit;cursor:pointer;"
        "background:var(--tg-theme-secondary-bg-color,rgba(128,128,128,.1));"
        "transition:opacity .2s ease}"
        ".i.dn{opacity:.52;cursor:default}"
        ".c{flex:0 0 22px;width:22px;height:22px;margin-top:1px;border-radius:6px;padding:0;"
        "border:2px solid var(--tg-theme-button-color,#2481cc);background:transparent;"
        "color:var(--tg-theme-button-text-color,#fff);font-size:13px;font-weight:700;"
        "display:flex;align-items:center;justify-content:center}"
        ".i.dn .c{background:var(--tg-theme-button-color,#2481cc);border-color:var(--tg-theme-button-color,#2481cc)}"
        ".i.ld .c{opacity:.55}"
        ".m{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1}"
        ".tag{font-size:11px;font-weight:700;color:var(--tg-theme-accent-text-color,var(--tg-theme-link-color,#2481cc))}"
        ".tx{word-break:break-word}"
        ".i.dn .tx{text-decoration:line-through;color:var(--tg-theme-hint-color,#888)}"
        ".ok{display:none;text-align:center;padding:12px 8px;font-weight:600;font-size:14px;"
        "border-radius:10px;background:var(--tg-theme-secondary-bg-color,rgba(128,128,128,.1));margin-top:8px}"
        ".er{display:none;margin-top:6px;font-size:12px;color:var(--tg-theme-destructive-text-color,#e53935)}"
        "</style></head><body>"
        f'<div class="hd"><div class="tt">{safe_title}</div>'
        f'<div class="rt"><span class="bd" id="cnt">{total} {html_lib.escape(left_label)}</span>'
        f'<button class="rf" id="rf" type="button">{refresh_label}</button></div></div>'
        '<div class="bar"><div class="bf" id="bf"></div></div>'
        f'<div class="ls" id="ls">{"".join(rows_html)}</div>'
        f'<div class="ok" id="ok">{html_lib.escape(all_done_text)}</div>'
        '<div class="er" id="er"></div>'
        "<script>"
        f"const W=window.TelegramWidget,IDS={ids_json},LOC={loc_json},LBL={left_json},ERR={err_json};"
        "let done=new Set(),busy=new Set();"
        "function ps(v){if(!v)return null;if(typeof v==='object')return v;try{return JSON.parse(v)}catch(e){return null}}"
        "function applyActive(a){if(!Array.isArray(a))return;const s=new Set(a);done=new Set(IDS.filter(x=>!s.has(x)));}"
        "function draw(){"
        "let rem=0;"
        "for(let k=0;k<IDS.length;k++){"
        "const id=IDS[k],r=document.getElementById('r'+id),b=document.getElementById('b'+id);"
        "if(!r||!b)continue;"
        "const isD=done.has(id),isB=busy.has(id);"
        "if(!isD)rem++;"
        "r.className='i'+(isD?' dn':'')+(isB?' ld':'');"
        "b.textContent=isD?'✓':(isB?'…':'');"
        "}"
        "const cnt=document.getElementById('cnt'),bf=document.getElementById('bf'),ok=document.getElementById('ok');"
        "if(cnt)cnt.textContent=rem+' '+LBL;"
        "if(bf)bf.style.width=Math.round(((IDS.length-rem)/Math.max(1,IDS.length))*100)+'%';"
        "if(ok)ok.style.display=rem===0?'block':'none';"
        "}"
        "function showErr(m){const e=document.getElementById('er');if(!e)return;e.textContent=m||'';e.style.display=m?'block':'none';}"
        "function sync(){const st=ps(W&&W.chatData);if(st&&Array.isArray(st.a))applyActive(st.a);draw();}"
        "function tap(id){"
        "if(done.has(id)||busy.has(id)||!W||!W.request)return;"
        "showErr('');busy.add(id);draw();"
        "W.request('c:'+LOC+':'+id).then(ans=>{"
        "busy.delete(id);"
        "const raw=(ans&&typeof ans==='object'&&'result' in ans)?ans.result:ans;"
        "const st=ps(raw);"
        "if(st&&Array.isArray(st.a)){applyActive(st.a);}else{done.add(id);}"
        "draw();"
        "},()=>{busy.delete(id);showErr(ERR);draw();});"
        "}"
        "for(let k=0;k<IDS.length;k++){const id=IDS[k],r=document.getElementById('r'+id);if(r)r.addEventListener('click',()=>tap(id));}"
        "const rf=document.getElementById('rf');"
        "if(rf)rf.addEventListener('click',()=>{"
        "if(!W||!W.request)return;showErr('');rf.textContent='…';"
        "W.request('r:'+LOC).then(ans=>{"
        "rf.textContent='↻';"
        "const raw=(ans&&typeof ans==='object'&&'result' in ans)?ans.result:ans;"
        "const st=ps(raw);if(st&&Array.isArray(st.a))applyActive(st.a);draw();"
        "},()=>{rf.textContent='↻';showErr(ERR);});"
        "});"
        "if(W&&W.onEvent)W.onEvent('chatDataChanged',sync);"
        "sync();"
        "</script></body></html>"
    )

    if "\x00" in widget_html:
        widget_html = widget_html.replace("\x00", "")

    raw_bytes = widget_html.encode("utf-8")
    if len(raw_bytes) > MAX_HTML_RAW_BYTES:
        print(f"Tasks widget HTML too large (raw={len(raw_bytes)}B > {MAX_HTML_RAW_BYTES}B), falling back.")
        return None

    compressed = zlib.compress(raw_bytes, 9)
    if len(compressed) > MAX_HTML_ZLIB_BYTES:
        print(f"Tasks widget HTML too large (zlib={len(compressed)}B > {MAX_HTML_ZLIB_BYTES}B), falling back.")
        return None

    return widget_html


def encode_active_chat_data(active_ids: Sequence[int]) -> str:
    """Encode active task IDs into a compact JSON string <= 1024 UTF-8 bytes."""
    ids_list = [int(x) for x in active_ids]
    payload = json.dumps({"a": ids_list}, separators=(",", ":"))
    while len(payload.encode("utf-8")) > MAX_CHAT_DATA_BYTES and ids_list:
        ids_list.pop()
        payload = json.dumps({"a": ids_list}, separators=(",", ":"))
    return payload


async def send_tasks_widget(
    bot_token: str,
    chat_id: int,
    tasks: Sequence[Any],
    loc_code: str,
    loc_name: str,
    lang: str,
    http_client: httpx.AsyncClient,
) -> bool:
    """Send the interactive HTML tasks widget via Telegram Bot API sendWidget.
    Returns True on success, False if widget could not be sent (caller should fall back).
    """
    if not bot_token:
        return False

    widget_html = build_tasks_widget_html(tasks, loc_code, loc_name, lang)
    if not widget_html:
        return False

    payload = {
        "chat_id": chat_id,
        "html": widget_html,
        "allow_queries": True,
    }
    try:
        resp = await http_client.post(
            f"https://api.telegram.org/bot{bot_token}/sendWidget",
            json=payload,
            timeout=httpx.Timeout(10.0, connect=4.0, read=8.0),
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            return True
        print(f"sendWidget failed (status={resp.status_code}): {data}")
        return False
    except Exception as e:
        print(f"sendWidget exception: {repr(e)}")
        return False


async def answer_widget_query(
    bot_token: str,
    widget_query_id: str,
    data: str,
    http_client: httpx.AsyncClient,
) -> bool:
    """Answer an incoming WidgetQuery via Telegram Bot API answerWidgetQuery."""
    if not bot_token or not widget_query_id:
        return False
    safe_data = data if len(data.encode("utf-8")) <= MAX_CHAT_DATA_BYTES else '{"ok":1}'
    try:
        resp = await http_client.post(
            f"https://api.telegram.org/bot{bot_token}/answerWidgetQuery",
            json={"widget_query_id": widget_query_id, "data": safe_data},
            timeout=httpx.Timeout(8.0, connect=3.0, read=6.0),
        )
        res = resp.json()
        if resp.status_code == 200 and res.get("ok"):
            return True
        print(f"answerWidgetQuery failed (status={resp.status_code}): {res}")
        return False
    except Exception as e:
        print(f"answerWidgetQuery exception: {repr(e)}")
        return False


async def edit_message_widget_data(
    bot_token: str,
    chat_id: int,
    message_id: int,
    chat_data: str,
    http_client: httpx.AsyncClient,
) -> bool:
    """Update persistent chat_data on a sent widget via editMessageWidgetData."""
    if not bot_token or not chat_id or not message_id:
        return False
    if len(chat_data.encode("utf-8")) > MAX_CHAT_DATA_BYTES:
        return False
    try:
        resp = await http_client.post(
            f"https://api.telegram.org/bot{bot_token}/editMessageWidgetData",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "chat_data": chat_data,
            },
            timeout=httpx.Timeout(8.0, connect=3.0, read=6.0),
        )
        res = resp.json()
        if resp.status_code == 200 and res.get("ok"):
            return True
        print(f"editMessageWidgetData failed (status={resp.status_code}): {res}")
        return False
    except Exception as e:
        print(f"editMessageWidgetData exception: {repr(e)}")
        return False
