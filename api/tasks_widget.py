# api/tasks_widget.py
# Interactive In-Chat Task Card Widget for /checktasks & /kchecktasks
# Works natively in all Telegram clients (private chats & groups).
# Rollback options:
#   1) Bot command (admin): /taskswidget off
#   2) Environment variable: TASKS_WIDGET_ENABLED=0
#   3) Git revert of this commit

import html as html_lib
import math
import os
from typing import Any, Optional, Sequence, Tuple
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

PAGE_SIZE = 6
MAX_BTN_TEXT_LEN = 34

BRANCH_TABS = [
    ("GN", "ԳՆ", "ГН"),
    ("K", "Կոմիտաս", "Комитас"),
    ("S", "Սայաթ-Նովա", "Саят-Нова"),
]

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
    """Return True if interactive task card widget is enabled.
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


def render_tasks_card(
    tasks: Sequence[Any],
    loc_code: str,
    loc_name: str,
    lang: str = "hy",
    page: int = 0,
    done_count: int = 0,
    initial_total: Optional[int] = None,
    last_done_id: Optional[int] = None,
) -> Tuple[str, InlineKeyboardMarkup]:
    """Build HTML text + InlineKeyboardMarkup for the interactive in-chat task card."""
    is_hy = (lang == "hy")
    title_suffix = "Առաջադրանքներ" if is_hy else "Задачи"
    remaining = len(tasks)

    # Keep session progress consistent if new tasks were added externally
    if initial_total is None or initial_total < remaining + done_count:
        total = remaining + done_count
    else:
        total = initial_total

    done_display = max(0, total - remaining) if total > 0 else done_count
    pct = int(round((done_display / total) * 100)) if total > 0 else 100
    bar = _render_progress_bar(done_display, total, width=10)

    safe_loc = html_lib.escape(str(loc_name))
    header = f"📋 <b>{safe_loc} · {title_suffix}</b>\n"

    if total == 0:
        empty_msg = "✨ Ակտիվ առաջադրանքներ չկան։" if is_hy else "✨ Активных задач нет."
        body = f"\n<blockquote>{empty_msg}</blockquote>"
        total_pages = 1
        page = 0
        page_tasks: Sequence[Any] = []
    elif remaining == 0:
        all_done_msg = "🎉 Բոլոր առաջադրանքները կատարված են։" if is_hy else "🎉 Все задачи выполнены!"
        progress_line = f"<code>{bar}</code> <b>{done_display}/{total}</b> · 100%\n"
        body = f"{progress_line}\n<blockquote>{all_done_msg}</blockquote>"
        total_pages = 1
        page = 0
        page_tasks = []
    else:
        if done_display > 0:
            left_word = f"մնաց {remaining}" if is_hy else f"осталось {remaining}"
            progress_line = f"<code>{bar}</code> <b>{done_display}/{total}</b> ({pct}%) · {left_word}\n"
        else:
            active_word = f"Ակտիվ՝ <b>{remaining}</b>" if is_hy else f"Активных: <b>{remaining}</b>"
            progress_line = f"<code>{bar}</code> {active_word}\n"

        total_pages = max(1, math.ceil(remaining / PAGE_SIZE))
        page = max(0, min(page, total_pages - 1))
        start = page * PAGE_SIZE
        page_tasks = tasks[start : start + PAGE_SIZE]

        lines = []
        for task in page_tasks:
            t_id = int(task["id"])
            t_desc = html_lib.escape(str(task["description"] or ""))
            lines.append(f"▫️ <b>#{t_id}</b> — {t_desc}")

        hint_line = (
            "\n<i>Սեղմեք առաջադրանքի վրա՝ կատարված նշելու համար</i>"
            if is_hy
            else "\n<i>Нажмите на задачу, чтобы отметить выполненной</i>"
        )
        done_note = ""
        if last_done_id is not None:
            done_note = (
                f"\n✅ <i>#{last_done_id} կատարված է</i>"
                if is_hy
                else f"\n✅ <i>#{last_done_id} выполнено</i>"
            )

        body = f"{progress_line}\n<blockquote>" + "\n".join(lines) + f"</blockquote>{done_note}{hint_line}"

    text = header + body

    # Safety clamp for Telegram 4096-char limit
    if len(text) > 4000:
        text = text[:3985] + "\n…</blockquote>"

    # Build inline keyboard
    builder = InlineKeyboardBuilder()
    row_sizes = []

    # 1. Task checkbox buttons (1 full-width button per task so text is clearly readable)
    for task in page_tasks:
        t_id = int(task["id"])
        label = _truncate_label(task["description"])
        builder.button(
            text=f"⬜ #{t_id} · {label}",
            callback_data=f"tw_c:{loc_code}:{t_id}:{page}:{done_display}:{total}",
        )
        row_sizes.append(1)

    # 2. Pagination row (only if more than 1 page)
    if total_pages > 1:
        prev_p = (page - 1) % total_pages
        next_p = (page + 1) % total_pages
        builder.button(text="◀️", callback_data=f"tw_p:{loc_code}:{prev_p}:{done_display}:{total}")
        builder.button(text=f"{page + 1} / {total_pages}", callback_data="tw_noop")
        builder.button(text="▶️", callback_data=f"tw_p:{loc_code}:{next_p}:{done_display}:{total}")
        row_sizes.append(3)

    # 3. Branch switcher row
    for code, name_hy, name_ru in BRANCH_TABS:
        b_name = name_hy if is_hy else name_ru
        prefix = "📍 " if code == loc_code else ""
        builder.button(text=f"{prefix}{b_name}", callback_data=f"tw_b:{code}")
    row_sizes.append(len(BRANCH_TABS))

    # 4. Refresh row
    refresh_label = "🔄 Թարմացնել" if is_hy else "🔄 Обновить"
    builder.button(
        text=refresh_label,
        callback_data=f"tw_r:{loc_code}:{page}:{done_display}:{total}",
    )
    row_sizes.append(1)

    builder.adjust(*row_sizes)
    return text, builder.as_markup()
