import asyncio
import os

WEBHOOK_PATH = r"C:\tgbot\api\webhook.py"

def main():
    with open(WEBHOOK_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # process_payment
    content = content.replace(
        '"Խնդրում ենք նախ գրանցել ձեր անունը՝ սեղմելով /start հրամանը:"',
        't("unreg_user", lang)'
    )
    content = content.replace(
        'ERROR_INSTRUCTION = (\n        "❌ **Սխալ ձևաչափ**\\n\\n"\n        "Վճարումը գրանցելու համար խնդրում ենք գրել ճիշտ հերթականությամբ՝\\n"\n        "👉 `Անուն Ազգանուն Գումար Եղանակ`\\n\\n"\n        "Օրինակ՝ `Aram Grigoryan 50000 N`\\n\\n"\n        "💳 **Հասանելի վճարման եղանակներ՝**\\n"\n        "• `n` — Կանխիկ (Наличные)\\n"\n        "• `b.n` — Տերմինալով (Безналичные)\\n"\n        "• `c` — Քարտով փոխանցում (Карта)\\n\\n"\n        "⚠️ Ուշադրություն դարձրեք, որ գումարը պետք է լինի միայն թվերով, իսկ եղանակը՝ նշված տարբերակներից մեկը։"\n    )',
        'ERROR_INSTRUCTION = t("payment_format_err", lang)'
    )
    content = content.replace(
        '"🔄 Կապվում եմ Alfa CRM-ի հետ..."',
        't("payment_processing", lang)'
    )
    content = content.replace(
        '"❌ Աշակերտը չգտնվեց նշված CRM ID-ով/հղումով:"',
        't("payment_not_found", lang)'
    )
    content = content.replace(
        'f"✅ Վճարումը հաջողությամբ գրանցվեց Alfa CRM-ում և ԴԴՍ-ում ({student_name}):\\n\\n{pending[\'response_text\']}"',
        't("payment_success", lang, name=student_name, text=pending["response_text"])'
    )
    content = content.replace(
        '"❌ Սխալ տեղի ունեցավ CRM-ում վճարումը գրանցելիս:"',
        't("payment_error", lang)'
    )
    content = content.replace(
        '"❌ Չհաջողվեց գտնել աշակերտի ID-ն:\\n"\\\n                    "Խնդրում ենք ուղարկել ճիշտ CRM անկետայի հղումը (օրինակ՝ `https://.../customer/view?id=12345`) կամ աշակերտի ID-ն:"',
        't("payment_pending", lang)'
    )
    content = content.replace(
        '"❌ Դուք չունեք սպասվող վճարում:\\n\\n"\\\n                    "Վճարումը գրանցելու համար խնդրում ենք գրել ճիշտ հերթականությամբ՝\\n"\\\n                    "👉 `Անուն Ազգանուն Գումար Եղանակ`"',
        't("payment_no_pending", lang) + "\\n\\n" + t("payment_format_err", lang)'
    )
    content = content.replace(
        '"🔄 Փնտրում եմ աշակերտին CRM-ում..."',
        't("payment_searching", lang)'
    )
    content = content.replace(
        '"❌ Աշակերտը չգտնվեց Alfa CRM-ում: Վճարումը հաստատելու համար խնդրում ենք ուղարկել նրա CRM անկետայի հղումը:"',
        't("payment_not_found", lang)'
    )
    content = content.replace(
        'f"❌ Գտնվել է «{customer_name}» աշակերտը, բայց նա {loc[\'name\']} մասնաճյուղից չէ: Վճարումը հաստատելու համար ուղարկեք նրա CRM անկետայի հղումը:"',
        't("payment_wrong_loc", lang, name=customer_name, loc=loc["name"])'
    )
    content = content.replace(
        'f"✅ Վճարումը հաջողությամբ գրանցվեց Alfa CRM-ում և ԴԴՍ-ում ({customer_name}):\\n\\n{response_text}"',
        't("payment_success", lang, name=customer_name, text=response_text)'
    )
    content = content.replace(
        'f"❌ Սխալ տեղի ունեցավ CRM-ում վճարումը գրանցելիս: Ստուգեք Alfa CRM-ը:"',
        't("payment_error", lang)'
    )
    
    # cmd_prob
    content = content.replace(
        'f"⚠️ **{loc[\'name\']}** — Փորձնական դասերի գրաֆիկը նշված չէ:\\n"\\\n            "Խնդրում ենք դիմել ադմինիստրատորին:"',
        't("prob_no_schedule", lang, loc=loc["name"])'
    )
    content = content.replace(
        '"Այսօրվա համար գրանցված փորձնական դասեր չկան:"',
        't("no_prob_today", lang)'
    )
    content = content.replace(
        '"🟢 **Այսօրվա գրանցված փորձնական դասերը**\\n\\n"',
        't("prob_today_header", lang) + "\\n\\n"'
    )
    content = content.replace(
        '"Այս շաբաթվա համար գրանցված փորձնական դասեր չկան:"',
        't("no_prob_week", lang)'
    )
    content = content.replace(
        '"🟢 **Այս շաբաթվա գրանցված փորձնական դասերը**\\n\\n"',
        't("prob_week_header", lang) + "\\n\\n"'
    )
    content = content.replace(
        '"🔄 Հաշվարկում եմ ազատ տեղերը..."',
        't("prob_freeprob", lang)'
    )
    content = content.replace(
        '"🟢 **Փորձնական դասերի ազատ տեղերը այս շաբաթվա համար**\\n\\n"',
        't("freeprob_header", lang) + "\\n\\n"'
    )
    content = content.replace(
        'async def cmd_prob(message: types.Message):\n    ',
        'async def cmd_prob(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    '
    )
    content = content.replace(
        'async def cmd_proball(message: types.Message):\n    ',
        'async def cmd_proball(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    '
    )
    content = content.replace(
        'async def cmd_freeprob(message: types.Message):\n    ',
        'async def cmd_freeprob(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    '
    )

    # cmd_addprobk
    content = content.replace(
        '"❌ **Սխալ ձևաչափ**\\n\\n"\\\n            "Օգտագործեք՝ `/addprobk <հեռախոս> <տեսակ> <ամսաթիվ> <ժամ>`\\n"\\\n            "Օրինակ՝ `/addprobk 077000700 mk 21.09 15`\\n\\n"\\\n            "Տեսակներ՝ `mk` (MakeBlock) կամ `lg` (LEGO Education)"',
        't("addprobk_format", lang)'
    )
    content = content.replace(
        '"❌ Սխալ տեսակ: Օգտագործեք `mk` կամ `lg`:"',
        't("invalid_type", lang)'
    )
    content = content.replace(
        '"🔄 Ստեղծում եմ (Կոմիտաս)..."',
        't("addprobk_creating", lang, loc=loc["name"])'
    )
    content = content.replace(
        'f"❌ Լիդ կամ հաճախորդ {phone_raw} համարով չգտնվեց:"',
        't("addprob_not_found", lang, phone=phone_raw)'
    )
    content = content.replace(
        'f"❌ Սխալ դասը ստեղծելիս: {err_msg}"',
        't("addprobk_err_create", lang, msg=err_msg)'
    )
    content = content.replace(
        'async def cmd_addprobk(message: types.Message):\n    if message.from_user.id',
        'async def cmd_addprobk(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    loc = await get_user_location(message.from_user.id)\n    if message.from_user.id'
    )

    # getweek / getprob
    content = content.replace(
        '"🔄 Բեռնում եմ այս շաբաթվա գրանցվածները..."',
        't("loading", lang)'
    )
    content = content.replace(
        '"❌ Սխալ՝ չհաջողվեց կապ հաստատել Alfa CRM-ի հետ:"',
        't("crm_error", lang)'
    )
    content = content.replace(
        'async def cmd_getweek(message: types.Message):\n    if message.from_user.id',
        'async def cmd_getweek(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    if message.from_user.id'
    )
    content = content.replace(
        'async def cmd_getprob(message: types.Message):\n    if message.from_user.id',
        'async def cmd_getprob(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    if message.from_user.id'
    )


    with open(WEBHOOK_PATH, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
