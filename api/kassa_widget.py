# api/kassa_widget.py
# Interactive In-Chat Cards for Kassa & Payments (payments, candidate selection, prefix confirm, /undo, /rc, /check)
# Rollback options:
#   1) Bot command (admin): /kassawidget off
#   2) Environment variable: KASSA_WIDGET_ENABLED=0
#   3) Git revert of this commit

import html as html_lib
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

_KASSA_WIDGET_ENABLED_CACHE: Optional[bool] = None


def _env_kassa_widget_override() -> Optional[bool]:
    raw = os.getenv("KASSA_WIDGET_ENABLED")
    if raw is None or raw.strip() == "":
        return None
    val = raw.strip().lower()
    if val in ("0", "false", "no", "off", "disabled"):
        return False
    if val in ("1", "true", "yes", "on", "enabled"):
        return True
    return None


async def is_kassa_widget_enabled(pool) -> bool:
    """Return True if interactive kassa/payments widget & cards are enabled."""
    global _KASSA_WIDGET_ENABLED_CACHE
    env_override = _env_kassa_widget_override()
    if env_override is not None:
        return env_override

    if _KASSA_WIDGET_ENABLED_CACHE is not None:
        return _KASSA_WIDGET_ENABLED_CACHE

    if pool is None:
        return True

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM bot_settings WHERE key = 'kassa_widget_enabled'"
            )
            if row is None:
                _KASSA_WIDGET_ENABLED_CACHE = True
            else:
                _KASSA_WIDGET_ENABLED_CACHE = str(row["value"]).strip().lower() not in ("0", "false", "off")
    except Exception as e:
        print(f"is_kassa_widget_enabled error: {e}")
        return True

    return _KASSA_WIDGET_ENABLED_CACHE


async def set_kassa_widget_enabled(pool, enabled: bool) -> bool:
    """Persist kassa widget feature flag in Postgres and update in-memory cache."""
    global _KASSA_WIDGET_ENABLED_CACHE
    _KASSA_WIDGET_ENABLED_CACHE = enabled
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_settings (key, value)
                VALUES ('kassa_widget_enabled', $1)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                "1" if enabled else "0",
            )
        return True
    except Exception as e:
        print(f"set_kassa_widget_enabled error: {e}")
        return False


def _fmt_amd(val: Any) -> str:
    try:
        num = float(val)
        if num.is_integer():
            return f"{int(num):,}".replace(",", " ")
        return f"{num:,.2f}".replace(",", " ")
    except Exception:
        return str(val)


def _truncate(text: str, max_len: int = 34) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def render_kassa_hub_card(
    loc_name: str,
    executor_name: str,
    lang: str = "hy",
    last_payment: Optional[Dict[str, Any]] = None,
    webapp_url: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build main Kassa hub card for /kassa command."""
    is_hy = (lang == "hy")
    safe_loc = html_lib.escape(str(loc_name))
    safe_exec = html_lib.escape(str(executor_name or "—"))

    title = "💳 <b>Դրամարկղ և Վճարումներ</b>" if is_hy else "💳 <b>Касса и Платежи</b>"
    sub = (
        f"📍 Մասնաճյուղ՝ <b>{safe_loc}</b> · 👤 <b>{safe_exec}</b>"
        if is_hy
        else f"📍 Филиал: <b>{safe_loc}</b> · 👤 <b>{safe_exec}</b>"
    )

    if is_hy:
        guide = (
            "<blockquote>"
            "💵 <b>Արագ վճարում տեքստով՝</b>\n"
            "<code>Անուն Ազգանուն Գումար n/b.n</code>\n"
            "<i>Օրինակ՝</i> <code>Aram Grigoryan 50000 n</code>\n\n"
            "💸 <b>Ծախս՝</b> <code>/rc [գումար] [պատճառ]</code>\n"
            "📊 <b>Ստուգում՝</b> <code>/check [գումար]</code>"
            "</blockquote>"
        )
    else:
        guide = (
            "<blockquote>"
            "💵 <b>Быстрая оплата текстом:</b>\n"
            "<code>Имя Фамилия Сумма n/b.n</code>\n"
            "<i>Пример:</i> <code>Aram Grigoryan 50000 n</code>\n\n"
            "💸 <b>Расход:</b> <code>/rc [сумма] [причина]</code>\n"
            "📊 <b>Сверка:</b> <code>/check [сумма]</code>"
            "</blockquote>"
        )

    last_block = ""
    if last_payment and last_payment.get("pay_id"):
        lp_name = html_lib.escape(str(last_payment.get("name", "")))
        lp_amt = _fmt_amd(last_payment.get("amount", 0))
        if is_hy:
            last_block = f"\n🧾 <i>Վերջին վճարումը՝</i> <b>{lp_name}</b> ({lp_amt} AMD)"
        else:
            last_block = f"\n🧾 <i>Последний платёж:</i> <b>{lp_name}</b> ({lp_amt} AMD)"

    text = f"{title}\n{sub}\n\n{guide}{last_block}"

    keyboard: List[List[Dict[str, Any]]] = []
    if webapp_url:
        sep = "&" if "?" in webapp_url else "?"
        keyboard.append([
            {
                "text": "✨ Բացել դրամարկղը (Mini App)" if is_hy else "✨ Открыть кассу (Mini App)",
                "web_app": {"url": f"{webapp_url}{sep}tab=pay"},
                "style": "primary",
            }
        ])
        keyboard.append([
            {
                "text": "💸 Ծախս (/rc)" if is_hy else "💸 Расход (/rc)",
                "web_app": {"url": f"{webapp_url}{sep}tab=rc"},
            },
            {
                "text": "📊 Ստուգում (/check)" if is_hy else "📊 Сверка (/check)",
                "web_app": {"url": f"{webapp_url}{sep}tab=check"},
            },
        ])

    keyboard.append([
        {
            "text": "📋 Ստուգել ԴԴՍ մնացորդը" if is_hy else "📋 Показать баланс ДДС",
            "callback_data": "kw_dds",
        }
    ])

    if last_payment and last_payment.get("pay_id"):
        keyboard.append([
            {
                "text": "🗑 Չեղարկել վերջին վճարումը" if is_hy else "🗑 Отменить последний платёж",
                "callback_data": "kw_undo",
                "style": "danger",
            }
        ])

    return text, {"inline_keyboard": keyboard}


def render_payment_receipt_card(
    customer_name: str,
    amount: int,
    method_label: str,
    executor_name: str,
    loc_name: str,
    lang: str = "hy",
    sheet_warning: str = "",
    webapp_url: Optional[str] = None,
    undone: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Build sleek HTML receipt card after a payment is recorded."""
    is_hy = (lang == "hy")
    safe_cust = html_lib.escape(str(customer_name))
    safe_loc = html_lib.escape(str(loc_name))
    safe_exec = html_lib.escape(str(executor_name))
    safe_method = html_lib.escape(str(method_label))
    amt_str = _fmt_amd(amount)

    if undone:
        header = "🗑 <b>Վճարումը չեղարկված է</b>" if is_hy else "🗑 <b>Платёж отменён</b>"
    else:
        header = "✅ <b>Վճարումը գրանցված է</b>" if is_hy else "✅ <b>Платёж зарегистрирован</b>"

    dds_ok = not bool(sheet_warning)
    status_str = "Alfa CRM ✅ · ԴԴՍ ✅" if dds_ok else "Alfa CRM ✅ · ԴԴՍ ⚠️"
    if undone:
        status_str = "Չեղարկված է / Отменён ❌"

    if is_hy:
        body = (
            "<blockquote>"
            f"👤 Աշակերտ՝ <b>{safe_cust}</b>\n"
            f"💰 Գումար՝ <b>{amt_str} AMD</b>\n"
            f"💳 Եղանակ՝ <b>{safe_method}</b>\n"
            f"📍 Մասնաճյուղ՝ <b>{safe_loc}</b>\n"
            f"👩‍💼 Ադմին՝ <b>{safe_exec}</b>\n"
            f"📊 Կարգավիճակ՝ <b>{status_str}</b>"
            "</blockquote>"
        )
    else:
        body = (
            "<blockquote>"
            f"👤 Ученик: <b>{safe_cust}</b>\n"
            f"💰 Сумма: <b>{amt_str} AMD</b>\n"
            f"💳 Способ: <b>{safe_method}</b>\n"
            f"📍 Филиал: <b>{safe_loc}</b>\n"
            f"👩‍💼 Админ: <b>{safe_exec}</b>\n"
            f"📊 Статус: <b>{status_str}</b>"
            "</blockquote>"
        )

    warn_block = ""
    if sheet_warning and not undone:
        safe_warn = html_lib.escape(str(sheet_warning))
        if is_hy:
            warn_block = f"\n⚠️ <b>Ուշադրություն․</b> Alfa CRM-ում գրանցվել է, բայց ԴԴՍ-ում առաջացավ սխալ․\n<code>{safe_warn}</code>"
        else:
            warn_block = f"\n⚠️ <b>Внимание:</b> В Alfa CRM записано, но в ДДС возникла ошибка:\n<code>{safe_warn}</code>"

    text = f"{header}\n\n{body}{warn_block}"

    keyboard: List[List[Dict[str, Any]]] = []
    if not undone:
        row: List[Dict[str, Any]] = [
            {
                "text": "🗑 Չեղարկել վճարումը" if is_hy else "🗑 Отменить платёж",
                "callback_data": "kw_undo",
                "style": "danger",
            }
        ]
        if webapp_url:
            row.append({
                "text": "💳 Դրամարկղ" if is_hy else "💳 Касса",
                "web_app": {"url": webapp_url},
                "style": "primary",
            })
        keyboard.append(row)
    elif webapp_url:
        keyboard.append([
            {
                "text": "💳 Բացել դրամարկղը" if is_hy else "💳 Открыть кассу",
                "web_app": {"url": webapp_url},
                "style": "primary",
            }
        ])

    return text, {"inline_keyboard": keyboard}


def render_candidates_card(
    candidates: Sequence[Dict[str, Any]],
    amount: int,
    method_label: str,
    loc_name: str,
    lang: str = "hy",
) -> Tuple[str, Dict[str, Any]]:
    """Build interactive candidate selection card when multiple students match."""
    is_hy = (lang == "hy")
    amt_str = _fmt_amd(amount)
    safe_method = html_lib.escape(str(method_label))
    safe_loc = html_lib.escape(str(loc_name))

    if is_hy:
        header = (
            "🔎 <b>Գտնվել են մի քանի աշակերտներ</b>\n"
            f"💰 Վճարում՝ <b>{amt_str} AMD</b> ({safe_method} · {safe_loc})\n\n"
        )
    else:
        header = (
            "🔎 <b>Найдено несколько учеников</b>\n"
            f"💰 Платёж: <b>{amt_str} AMD</b> ({safe_method} · {safe_loc})\n\n"
        )

    lines = []
    keyboard: List[List[Dict[str, Any]]] = []

    for idx, c in enumerate(candidates[:10]):
        c_name = str(c.get("name") or "—")
        c_id = c.get("id")
        phones = c.get("phone", [])
        if phones and isinstance(phones, list):
            p_str = ", ".join(str(p) for p in phones)
        elif phones:
            p_str = str(phones)
        else:
            p_str = ""

        safe_c_name = html_lib.escape(c_name)
        phone_part = f" · 📞 <code>{html_lib.escape(p_str)}</code>" if p_str else ""
        lines.append(f"<b>{idx + 1}.</b> {safe_c_name} (ID: <code>{c_id}</code>){phone_part}")

        btn_label = _truncate(f"{idx + 1}. {c_name} ({c_id})", 38)
        keyboard.append([
            {
                "text": f"👤 {btn_label}",
                "callback_data": f"kw_sel:{idx}",
                "style": "primary",
            }
        ])

    if len(candidates) > 10:
        more = len(candidates) - 10
        lines.append(f"<i>… +{more}</i>")

    hint = (
        "\n<i>Սեղմեք համապատասխան կոճակին կամ ուղարկեք համարը՝</i>"
        if is_hy
        else "\n<i>Нажмите на нужного ученика ниже или отправьте его номер:</i>"
    )

    keyboard.append([
        {
            "text": "❌ Չեղարկել" if is_hy else "❌ Отмена",
            "callback_data": "kw_cancel",
            "style": "danger",
        }
    ])

    text = header + "<blockquote>" + "\n".join(lines) + "</blockquote>" + hint
    return text, {"inline_keyboard": keyboard}


def render_confirm_prefix_card(
    customer_name: str,
    crm_prefix: str,
    amount: int,
    method_label: str,
    lang: str = "hy",
) -> Tuple[str, Dict[str, Any]]:
    """Build confirmation card when student lacks the branch CRM prefix."""
    is_hy = (lang == "hy")
    safe_name = html_lib.escape(str(customer_name))
    safe_pref = html_lib.escape(str(crm_prefix))
    amt_str = _fmt_amd(amount)
    safe_method = html_lib.escape(str(method_label))

    if is_hy:
        text = (
            "⚠️ <b>Պրեֆիքսի ստուգում</b>\n\n"
            "<blockquote>"
            f"👤 Աշակերտ՝ <b>{safe_name}</b>\n"
            f"💰 Գումար՝ <b>{amt_str} AMD</b> ({safe_method})\n"
            f"🏷 Բացակայում է՝ <code>{safe_pref} |</code>"
            "</blockquote>\n"
            f"Ավելացնե՞լ «<b>{safe_pref}</b>» պրեֆիքսը և գրանցել վճարումը:"
        )
        yes_lbl = f"✅ Այո, ավելացնել {crm_prefix}"
        no_lbl = "❌ Ոչ, այլ աշակերտ է"
    else:
        text = (
            "⚠️ <b>Проверка префикса филиала</b>\n\n"
            "<blockquote>"
            f"👤 Клиент: <b>{safe_name}</b>\n"
            f"💰 Сумма: <b>{amt_str} AMD</b> ({safe_method})\n"
            f"🏷 Нет префикса: <code>{safe_pref} |</code>"
            "</blockquote>\n"
            f"Добавить префикс «<b>{safe_pref}</b>» и провести оплату?"
        )
        yes_lbl = f"✅ Да, добавить {crm_prefix}"
        no_lbl = "❌ Нет, другой клиент"

    keyboard = [
        [
            {"text": yes_lbl, "callback_data": "conf_yes", "style": "success"},
            {"text": no_lbl, "callback_data": "conf_no", "style": "danger"},
        ]
    ]
    return text, {"inline_keyboard": keyboard}


def render_expense_card(
    amount: int,
    reason: str,
    loc_name: str,
    executor_name: str,
    lang: str = "hy",
    webapp_url: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build HTML card after recording an expense via /rc."""
    is_hy = (lang == "hy")
    amt_str = _fmt_amd(amount)
    safe_reason = html_lib.escape(str(reason))
    safe_loc = html_lib.escape(str(loc_name))
    safe_exec = html_lib.escape(str(executor_name))

    if is_hy:
        text = (
            "💸 <b>Ծախսը գրանցված է (ԴԴՍ)</b>\n\n"
            "<blockquote>"
            f"💰 Գումար՝ <b>{amt_str} AMD</b>\n"
            f"📝 Պատճառ՝ <b>{safe_reason}</b>\n"
            f"📍 Մասնաճյուղ՝ <b>{safe_loc}</b>\n"
            f"👤 Ավելացրեց՝ <b>{safe_exec}</b>"
            "</blockquote>"
        )
    else:
        text = (
            "💸 <b>Расход успешно записан в ДДС</b>\n\n"
            "<blockquote>"
            f"💰 Сумма: <b>{amt_str} AMD</b>\n"
            f"📝 Причина: <b>{safe_reason}</b>\n"
            f"📍 Филиал: <b>{safe_loc}</b>\n"
            f"👤 Добавил(а): <b>{safe_exec}</b>"
            "</blockquote>"
        )

    keyboard: List[List[Dict[str, Any]]] = []
    if webapp_url:
        sep = "&" if "?" in webapp_url else "?"
        keyboard.append([
            {
                "text": "💳 Բացել դրամարկղը" if is_hy else "💳 Открыть кассу",
                "web_app": {"url": f"{webapp_url}{sep}tab=rc"},
                "style": "primary",
            }
        ])
    return text, {"inline_keyboard": keyboard}


def render_kassa_check_card(
    last_h: Any,
    summ: Any,
    match: bool,
    diff_text: str,
    loc_name: str,
    lang: str = "hy",
    webapp_url: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build HTML card for /check cash reconciliation result."""
    is_hy = (lang == "hy")
    safe_loc = html_lib.escape(str(loc_name))
    dds_str = _fmt_amd(last_h)
    fact_str = _fmt_amd(summ)
    safe_diff = html_lib.escape(str(diff_text))

    if match:
        badge = "✅ <b>Գումարները համընկնում են!</b>" if is_hy else "✅ <b>Суммы совпадают!</b>"
    else:
        badge = (
            f"❌ <b>Ուշադրություն! Գումարները ՉԵՆ համընկնում{safe_diff}</b>"
            if is_hy
            else f"❌ <b>Внимание! Суммы НЕ совпадают!{safe_diff}</b>"
        )

    if is_hy:
        text = (
            f"📊 <b>Դրամարկղի ստուգում · {safe_loc}</b>\n\n"
            "<blockquote>"
            f"📋 Ըստ ԴԴՍ-ի՝ <b>{dds_str} AMD</b>\n"
            f"💵 Փաստացի՝ <b>{fact_str} AMD</b>"
            "</blockquote>\n"
            f"{badge}"
        )
    else:
        text = (
            f"📊 <b>Сверка кассы · {safe_loc}</b>\n\n"
            "<blockquote>"
            f"📋 По ДДС: <b>{dds_str} AMD</b>\n"
            f"💵 Касса факт: <b>{fact_str} AMD</b>"
            "</blockquote>\n"
            f"{badge}"
        )

    keyboard: List[List[Dict[str, Any]]] = []
    if webapp_url:
        sep = "&" if "?" in webapp_url else "?"
        keyboard.append([
            {
                "text": "📊 Բացել դրամարկղը" if is_hy else "📊 Открыть кассу",
                "web_app": {"url": f"{webapp_url}{sep}tab=check"},
                "style": "primary",
            }
        ])
    return text, {"inline_keyboard": keyboard}
