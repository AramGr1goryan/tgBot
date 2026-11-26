# api/tasks_widget.py
# Interactive In-Chat Task Card Widget (Bot API 9.4+ colored buttons + priority filters)
# Rollback options:
#   1) Bot command (admin): /taskswidget off
#   2) Environment variable: TASKS_WIDGET_ENABLED=0
#   3) Git revert of this commit

import html as html_lib
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple
import httpx

PAGE_SIZE = 6
MAX_BTN_TEXT_LEN = 32

# Priority metadata: code -> (rank, emoji, label_ru, label_hy, tg_button_style)
PRIORITY_META = {
    "C": (0, "🔴", "Critical", "Critical", "danger"),
    "H": (1, "🟠", "High", "High", "primary"),
    "N": (2, "🟢", "Normal", "Normal", "success"),
}

# Strictly ASCII/Latin tokens so Cyrillic 'С' (Russian preposition) is NEVER misread as Critical
_PRIORITY_TOKENS = {
    "c": "C",
    "-c": "C",
    "c:": "C",
    "crit": "C",
    "critical": "C",
    "h": "H",
    "-h": "H",
    "h:": "H",
    "high": "H",
    "n": "N",
    "-n": "N",
    "n:": "N",
    "norm": "N",
    "normal": "N",
}

_WIDGET_ENABLED_CACHE: Optional[bool] = None


def normalize_priority(value: Any) -> str:
    raw = str(value or "N").strip().upper()
    if raw in ("C", "CRITICAL", "CRIT"):
        return "C"
    if raw in ("H", "HIGH"):
        return "H"
    return "N"


def priority_badge(priority: str) -> str:
    p = normalize_priority(priority)
    _, emoji, label, _, _ = PRIORITY_META[p]
    return f"{emoji} {label}"


def parse_task_input(raw_text: str) -> Tuple[str, str]:
    """Parse optional priority token (N/H/C) from start or end of task description.

    Returns (priority_code, clean_description).
    Only ASCII/Latin tokens are matched so Russian 'С ...' is preserved intact.
    """
    text = (raw_text or "").strip()
    if not text:
        return "N", ""

    tokens = text.split()
    if len(tokens) >= 2:
        first_key = tokens[0].lower()
        if first_key.isascii() and first_key in _PRIORITY_TOKENS:
            rest = text[len(tokens[0]):].strip()
            if rest:
                return _PRIORITY_TOKENS[first_key], rest

        last_key = tokens[-1].lower()
        if last_key.isascii() and last_key in _PRIORITY_TOKENS:
            rest = text[: len(text) - len(tokens[-1])].strip()
            if rest:
                return _PRIORITY_TOKENS[last_key], rest

    return "N", text


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
    """Return True if interactive task card widget is enabled."""
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


def _render_progress_bar(done: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "▓" * width
    ratio = max(0.0, min(1.0, done / total))
    filled = int(round(ratio * width))
    return ("▓" * filled) + ("░" * (width - filled))


def _truncate_label(text: str, max_len: int = MAX_BTN_TEXT_LEN) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def _task_priority(task: Any) -> str:
    try:
        val = task["priority"]
    except (KeyError, IndexError, TypeError):
        val = "N"
    return normalize_priority(val)


def render_tasks_card(
    tasks: Sequence[Any],
    loc_code: str,
    loc_name: str,
    lang: str = "hy",
    priority_filter: str = "A",
    page: int = 0,
    done_count: int = 0,
    initial_total: Optional[int] = None,
    last_done_id: Optional[int] = None,
    webapp_url: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build HTML text + raw Telegram reply_markup dict (with Bot API 9.4+ colored button styles)."""
    is_hy = (lang == "hy")
    title_suffix = "Առաջադրանքներ" if is_hy else "Задачи"

    flt = priority_filter.upper() if priority_filter else "A"
    if flt not in ("A", "C", "H", "N"):
        flt = "A"

    # Sort all tasks by priority (C -> H -> N), then id
    sorted_tasks = sorted(tasks, key=lambda item: (PRIORITY_META[_task_priority(item)][0], int(item["id"])))

    counts = {"C": 0, "H": 0, "N": 0}
    for item in sorted_tasks:
        counts[_task_priority(item)] += 1

    all_remaining = len(sorted_tasks)
    if initial_total is None or initial_total < all_remaining + done_count:
        total = all_remaining + done_count
    else:
        total = initial_total

    done_display = max(0, total - all_remaining) if total > 0 else done_count
    pct = int(round((done_display / total) * 100)) if total > 0 else 100
    bar = _render_progress_bar(done_display, total, width=10)

    filtered_tasks = sorted_tasks if flt == "A" else [x for x in sorted_tasks if _task_priority(x) == flt]
    filtered_count = len(filtered_tasks)

    safe_loc = html_lib.escape(str(loc_name))
    header = f"📋 <b>{safe_loc} · {title_suffix}</b>\n"
    stats_line = f"🔴 <b>{counts['C']}</b> · 🟠 <b>{counts['H']}</b> · 🟢 <b>{counts['N']}</b>"

    if total == 0:
        empty_msg = "✨ Ակտիվ առաջադրանքներ չկան։" if is_hy else "✨ Активных задач нет."
        body = f"\n<blockquote>{empty_msg}</blockquote>"
        total_pages = 1
        page = 0
        page_tasks: List[Any] = []
    elif all_remaining == 0:
        all_done_msg = "🎉 Բոլոր առաջադրանքները կատարված են։" if is_hy else "🎉 Все задачи выполнены!"
        progress_line = f"<code>{bar}</code> <b>{done_display}/{total}</b> · 100%\n"
        body = f"{progress_line}\n<blockquote>{all_done_msg}</blockquote>"
        total_pages = 1
        page = 0
        page_tasks = []
    else:
        if done_display > 0:
            progress_line = f"<code>{bar}</code> <b>{done_display}/{total}</b> ({pct}%) · {stats_line}\n"
        else:
            progress_line = f"<code>{bar}</code> {stats_line}\n"

        filter_badge = ""
        if flt != "A":
            _, f_emoji, f_label, _, _ = PRIORITY_META[flt]
            flt_word = "Ֆիլտր՝" if is_hy else "Фильтр:"
            filter_badge = f"<i>{flt_word} {f_emoji} {f_label}</i>\n"

        total_pages = max(1, math.ceil(filtered_count / PAGE_SIZE))
        page = max(0, min(page, total_pages - 1))
        start = page * PAGE_SIZE
        page_tasks = filtered_tasks[start : start + PAGE_SIZE]

        if not page_tasks:
            no_flt_msg = "Այս կարևորությամբ առաջադրանքներ չկան։" if is_hy else "Задач с этой критичностью нет."
            blocks_html = f"<blockquote>{no_flt_msg}</blockquote>"
        else:
            # Group displayed tasks into clean blockquotes by priority
            grouped: Dict[str, List[Any]] = {"C": [], "H": [], "N": []}
            for task in page_tasks:
                grouped[_task_priority(task)].append(task)

            blocks = []
            for p_code in ("C", "H", "N"):
                grp = grouped[p_code]
                if not grp:
                    continue
                _, p_emoji, p_label, _, _ = PRIORITY_META[p_code]
                lines = [f"{p_emoji} <b>{p_label.upper()}</b>"]
                for task in grp:
                    t_id = int(task["id"])
                    t_desc = html_lib.escape(str(task["description"] or ""))
                    lines.append(f"<b>#{t_id}</b> — {t_desc}")
                blocks.append("<blockquote>" + "\n".join(lines) + "</blockquote>")
            blocks_html = "\n".join(blocks)

        done_note = ""
        if last_done_id is not None:
            done_note = (
                f"\n✅ <i>#{last_done_id} կատարված է</i>"
                if is_hy
                else f"\n✅ <i>#{last_done_id} выполнено</i>"
            )

        hint_line = (
            "\n<i>Սեղմեք կոճակին՝ առաջադրանքը կատարված նշելու համար</i>"
            if is_hy
            else "\n<i>Нажмите на задачу, чтобы отметить выполненной</i>"
        )
        body = f"{progress_line}{filter_badge}\n{blocks_html}{done_note}{hint_line}"

    text = header + body
    if len(text) > 4000:
        text = text[:3985] + "\n…</blockquote>"

    # Build raw Telegram InlineKeyboardMarkup dict (supports Bot API 9.4+ style colors)
    keyboard: List[List[Dict[str, Any]]] = []

    # 1. Task completion buttons (colored by priority: danger=red, primary=blue, success=green)
    for task in page_tasks:
        t_id = int(task["id"])
        p_code = _task_priority(task)
        _, p_emoji, _, _, btn_style = PRIORITY_META[p_code]
        label = _truncate_label(task["description"])
        keyboard.append([
            {
                "text": f"{p_emoji} #{t_id} · {label}",
                "callback_data": f"tw_c:{loc_code}:{t_id}:{flt}:{page}:{done_display}:{total}",
                "style": btn_style,
            }
        ])

    # 2. Pagination row (only when > 1 page)
    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        keyboard.append([
            {"text": "◀️", "callback_data": f"tw_p:{loc_code}:{flt}:{prev_p}:{done_display}:{total}"},
            {"text": f"{page + 1} / {total_pages}", "callback_data": "tw_noop"},
            {"text": "▶️", "callback_data": f"tw_p:{loc_code}:{flt}:{next_p}:{done_display}:{total}"},
        ])

    # 3. Priority filter row (only when there are active tasks)
    if all_remaining > 0:
        all_word = "Բոլորը" if is_hy else "Все"
        filter_row: List[Dict[str, Any]] = []
        filter_specs = [
            ("A", f"{all_word} {all_remaining}", None),
            ("C", f"🔴 {counts['C']}", "danger"),
            ("H", f"🟠 {counts['H']}", "primary"),
            ("N", f"🟢 {counts['N']}", "success"),
        ]
        for code, lbl, active_style in filter_specs:
            is_active = (flt == code)
            btn: Dict[str, Any] = {
                "text": f"• {lbl}" if is_active else lbl,
                "callback_data": f"tw_f:{loc_code}:{code}:{done_display}:{total}",
            }
            if is_active and active_style:
                btn["style"] = active_style
            filter_row.append(btn)
        keyboard.append(filter_row)

    # 4. Action row: Mini App board button (private chat only) + Refresh button
    action_row: List[Dict[str, Any]] = []
    if webapp_url:
        board_label = "✨ Բացել տախտակը" if is_hy else "✨ Открыть доску"
        action_row.append({
            "text": board_label,
            "web_app": {"url": webapp_url},
            "style": "primary",
        })
    refresh_label = "🔄 Թարմացնել" if is_hy else "🔄 Обновить"
    action_row.append({
        "text": refresh_label,
        "callback_data": f"tw_r:{loc_code}:{flt}:{page}:{done_display}:{total}",
    })
    keyboard.append(action_row)

    return text, {"inline_keyboard": keyboard}


def _strip_button_styles(reply_markup: Dict[str, Any]) -> Dict[str, Any]:
    clean_rows = []
    for row in reply_markup.get("inline_keyboard", []):
        clean_rows.append([{k: v for k, v in btn.items() if k != "style"} for btn in row])
    return {"inline_keyboard": clean_rows}


async def send_card_message(
    bot_token: str,
    chat_id: int,
    text: str,
    reply_markup: Dict[str, Any],
    http_client: httpx.AsyncClient,
) -> bool:
    """Send HTML card via raw Telegram Bot API so colored button styles are preserved."""
    if not bot_token:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
    }
    try:
        resp = await http_client.post(url, json=payload, timeout=httpx.Timeout(10.0, connect=4.0, read=8.0))
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            return True
        payload["reply_markup"] = _strip_button_styles(reply_markup)
        resp2 = await http_client.post(url, json=payload, timeout=httpx.Timeout(10.0, connect=4.0, read=8.0))
        data2 = resp2.json()
        if resp2.status_code == 200 and data2.get("ok"):
            return True
        print(f"send_card_message failed: {data} / retry: {data2}")
        return False
    except Exception as e:
        print(f"send_card_message exception: {repr(e)}")
        return False


async def edit_card_message(
    bot_token: str,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: Dict[str, Any],
    http_client: httpx.AsyncClient,
) -> bool:
    """Edit HTML card via raw Telegram Bot API so colored button styles are preserved."""
    if not bot_token:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
    }
    try:
        resp = await http_client.post(url, json=payload, timeout=httpx.Timeout(10.0, connect=4.0, read=8.0))
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            return True
        desc = str(data.get("description", "")).lower()
        if "message is not modified" in desc:
            return True
        payload["reply_markup"] = _strip_button_styles(reply_markup)
        resp2 = await http_client.post(url, json=payload, timeout=httpx.Timeout(10.0, connect=4.0, read=8.0))
        data2 = resp2.json()
        if resp2.status_code == 200 and data2.get("ok"):
            return True
        if "message is not modified" in str(data2.get("description", "")).lower():
            return True
        print(f"edit_card_message failed: {data} / retry: {data2}")
        return False
    except Exception as e:
        print(f"edit_card_message exception: {repr(e)}")
        return False
