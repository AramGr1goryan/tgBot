import asyncio
import os

WEBHOOK_PATH = r"C:\tgbot\api\webhook.py"

def main():
    with open(WEBHOOK_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # cmd_add_student_to_group
    content = content.replace(
        'f"👥 **Ավելացնել աշակերտին խմբում (Alfa CRM - {loc[\'name\']}):**\\n\\n"\\\n            f"⚠️ **Ուշադրություն!** Խումբը և աշակերտը պետք է CRM-ում ունենան **{loc[\'crm_prefix\']}** պրեֆիքս:\\n\\n"\\\n            "Խնդրում ենք գրել հետևյալ ձևաչափով՝\\n"\\\n            "👉 `/add Saakyan Gexam Lego 1`\\n\\n"\\\n            "**Օրինակներ՝**\\n"\\\n            "• `/add Saakyan Gexam Lego 1`\\n"\\\n            "• `/add Lego 1, Saakyan Gexam`\\n"\\\n            "• `/add 3402, Lego 1`"',
        't("add_help", lang, loc=loc["name"], prefix=loc["crm_prefix"])'
    )
    content = content.replace(
        'f"🔄 Փնտրում եմ խումբը և աշակերտին Alfa CRM-ում ({loc[\'name\']})..."',
        't("add_searching", lang, loc=loc["name"])'
    )
    content = content.replace(
        'f"❌ «{raw_args}» հարցման մեջ խումբը չգտնվեց {loc[\'name\']} մասնաճյուղում:\\n"\\\n            "Ստուգեք խմբի անվանման ճշտությունը:"',
        't("add_group_not_found", lang, query=raw_args, loc=loc["name"])'
    )
    content = content.replace(
        'f"❌ «{raw_args}» հարցման մեջ աշակերտի անունը/ID-ն նշված չէ:"',
        't("add_no_student_q", lang, query=raw_args)'
    )
    content = content.replace(
        'f"❌ «{student_query}» աշակերտը/լիդը չգտնվեց Alfa CRM-ում:\\n"\\\n            "Ստուգեք անվանման ճշտությունը կամ ուղարկեք ID-ն:"',
        't("add_student_not_found", lang, query=student_query)'
    )
    content = content.replace(
        'f"⚠️ **«{group_name}» խումբը չունի «{loc[\'crm_prefix\']}» պրեֆիքս!**\\n\\n"\\\n            f"Ավելացումն արգելափակված է: Խնդրում ենք նախ Alfa CRM-ում խմբի անվանման սկզբում ավելացնել «{loc[\'crm_prefix\']}» (օրինակ՝ `{loc[\'crm_prefix\']} | {group_name}`) և կրկնել հրամանը:"',
        't("add_no_prefix_grp", lang, group=group_name, prefix=loc["crm_prefix"])'
    )
    content = content.replace(
        'f"⚠️ **«{customer_name}» աշակերտը չունի «{loc[\'crm_prefix\']}» պրեֆիքս!**\\n\\n"\\\n            f"Ավելացումն արգելափակված է: Խնդրում ենք նախ Alfa CRM-ում աշակերտի անվանման սկզբում ավելացնել «{loc[\'crm_prefix\']}» (օրինակ՝ `{loc[\'crm_prefix\']} | {customer_name}`) և կրկնել հրամանը:"',
        't("add_no_prefix_std", lang, student=customer_name, prefix=loc["crm_prefix"])'
    )
    content = content.replace(
        'f"✅ **Հաջողությամբ ավելացվեց!**\\n\\n"\\\n                f"👤 Աշակերտ՝ **{customer_name}**\\n"\\\n                f"👥 Խումբ՝ **{group_name}**"',
        't("add_success", lang, student=customer_name, group=group_name)'
    )
    content = content.replace(
        'f"ℹ️ «{customer_name}» աշակերտը արդեն իսկ գտնվում է «{group_name}» խմբում:"',
        't("add_already", lang, student=customer_name, group=group_name)'
    )
    content = content.replace(
        'f"❌ Սխալ տեղի ունեցավ «{customer_name}» աշակերտին «{group_name}» խմբում ավելացնելիս:\\n`{msg}`"',
        't("add_error", lang, student=customer_name, group=group_name, msg=msg)'
    )

    # cmd_ban & cmd_unban & cmd_getusers
    content = content.replace(
        '"Նշեք օգտատիրոջ ID-ն: Օրինակ՝ /ban 123456789"',
        't("ban_format", lang)'
    )
    content = content.replace(
        '"Դուք չեք կարող բլոկավորել ինքներդ ձեզ:"',
        't("ban_self", lang)'
    )
    content = content.replace(
        'f"✅ Օգտատեր {target_id}-ը բլոկավորված է և չի կարող օգտվել բոտից:"',
        't("ban_success", lang, uid=target_id)'
    )
    content = content.replace(
        'async def cmd_ban(message: types.Message):\n    if message.from_user.id',
        'async def cmd_ban(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    if message.from_user.id'
    )

    content = content.replace(
        '"Նշեք օգտատիրոջ ID-ն: Օրինակ՝ /unban 123456789"',
        't("unban_format", lang)'
    )
    content = content.replace(
        'f"✅ Օգտատեր {target_id}-ի բլոկավորումը հանված է:"',
        't("unban_success", lang, uid=target_id)'
    )
    content = content.replace(
        'async def cmd_unban(message: types.Message):\n    if message.from_user.id',
        'async def cmd_unban(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    if message.from_user.id'
    )

    content = content.replace(
        '"Ակտիվ օգտատերեր չկան (ոչ ոք դեռ չի գրել բոտին):"',
        't("no_users", lang)'
    )
    content = content.replace(
        '"Բոլոր օգտատերերը (Անուն - ID)՝\\n\\n"',
        't("users_header", lang)'
    )
    content = content.replace(
        'async def cmd_getusers(message: types.Message):\n    if message.from_user.id',
        'async def cmd_getusers(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    if message.from_user.id'
    )

    # lego
    content = content.replace(
        '"Նշեք խմբի անունը, օրինակ՝ /lego Spider man"',
        't("lego_format", lang)'
    )
    content = content.replace(
        'f"«{group_query}» խումբը չի գտնվել բազայում:"',
        't("lego_not_found", lang, group=group_query)'
    )
    content = content.replace(
        'f"«{group_name}» խմբում հասանելի թեմաներ չկան (կամ բոլորն արդեն անցել են):"',
        't("lego_no_themes", lang, group=group_name)'
    )
    content = content.replace(
        'f"Հասանելի թեմաներ «{group_name}» խմբի համար:\\n{themes_list}\\n\\nԳրեք այն թեմայի անվանումը, որն ընտրել եք:"',
        't("lego_themes_list", lang, group=group_name, list=themes_list)'
    )
    content = content.replace(
        'async def cmd_lego(message: types.Message):\n    \n    group_query',
        'async def cmd_lego(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    group_query'
    )

    content = content.replace(
        '"Սխալ․ խումբը բազայում չի գտնվել։"',
        't("lego_err_group", lang)'
    )
    content = content.replace(
        'f"✅ «{theme_choice}» թեման ընտրված և հեռացված է «{group_name}» խմբից:"',
        't("lego_theme_selected", lang, theme=theme_choice, group=group_name)'
    )
    content = content.replace(
        'f"❌ «{theme_choice}» թեման չի գտնվել «{group_name}» խմբում։ Համոզվեք, որ այն ճիշտ եք գրել։"',
        't("lego_theme_invalid", lang, theme=theme_choice, group=group_name)'
    )
    content = content.replace(
        'async def process_theme_selection(message: types.Message):\n        \n    original_text',
        'async def process_theme_selection(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    original_text'
    )

    with open(WEBHOOK_PATH, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
