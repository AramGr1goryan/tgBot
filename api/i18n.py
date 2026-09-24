# api/i18n.py
# Система переводов: армянский (hy) и русский (ru).
# Дефолт: армянский (текущий язык бота).

STRINGS: dict = {
    "hy": {
        # ── Локация (/branch) ──────────────────────────────────────────
        "location_set":       "✅ Lokacija'-n patasxvec e: **{name}**",
        "location_invalid":   "❌ Ancejayt lokacija': `{code}`\nOgtagortsuyk'e': `gn`, `k`, `s`",
        "location_current":   "📍 Aktiv lokacija': **{name}**\n\nAnhunacek':",
        "location_choose":    "Anhunacek' lokacija'-n:",

        # ── Язык (/language) ──────────────────────────────────────────
        "language_set":       "✅ Lezun patasxvec e",
        "language_choose":    "Anhunacek' lezun:",

        # ── Платёж (process_payment) ──────────────────────────────────
        "payment_searching":  "🔄 Patrvasum em Alfa CRM-um...",
        "payment_not_found":  "❌ {phone} hamarov lid kam hachagor char gtanvec:",
        "payment_wrong_loc":  (
            "❌ Gtanvec e «{name}», bayc na «{loc}» lokaciajic' che:\n"
            "Vcharumu'n hascecnelu hamar uuarcek' CRM qartahasy:"
        ),
        "payment_success":    "✅ Vcharumu'n hajoxutyamb grancvec Alfa CRM-um ev DDS-um ({name}):\n\n{text}",
        "payment_error":      "❌ Sxal CRM-um vcharum grancvelu:",
        "payment_pending":    (
            "❌ Ashakerty char gtanvec Alfa CRM-um:\n"
            "Vcharumu'n hascecnelu hamar uuarcek' CRM qartahasy:"
        ),

        # ── /addprob ──────────────────────────────────────────────────
        "addprob_searching":  "🔄 Patrvasum em...",
        "addprob_not_found":  "❌ {phone} hamarov lid kam hachagor char gtanvec:",
        "addprob_no_lesson":  "❌ Pordznayin das «{lesson}» nshvac zhamanakn char gtanvec ({dt}):",
        "addprob_added": (
            "✅ **Hajoxutyamb avelajvec!**\n\n"
            "👤 **Ashakert:** {student}\n"
            "📚 **Das:** Pordznayin {lesson}\n"
            "📅 **Zhamanak:** {dt}\n"
            "📍 **Lokacija:** {loc}"
        ),
        "addprob_already":    "⚠️ Ashakerty ({name}) ardem grancvac e ays dasin:",
        "addprob_error":      "❌ Sxal dasin avelajnelu: {msg}",

        # ── /add (добавить студента в группу) ─────────────────────────
        "add_no_prefix_grp": (
            "⚠️ **«{group}» khmby chuni «{prefix}» prefiksy!**\n\n"
            "Avelajumy argelakrvac e: Khndrum enq nakhevn Alfa CRM-um "
            "khmbى anvanman skzbum avelajnel «{prefix}» "
            "(orinak'` `{prefix} | {group}`) ev krknel haranken:"
        ),
        "add_no_prefix_std": (
            "⚠️ **«{student}» ashakerty chuni «{prefix}» prefiksy!**\n\n"
            "Avelajumy argelakrvac e: Khndrum enq nakhevn Alfa CRM-um "
            "ashakerty anvanman skzbum avelajnel «{prefix}» "
            "(orinak'` `{prefix} | {student}`) ev krknel haranken:"
        ),
        "add_success": (
            "✅ **Hajoxutyamb avelajvec!**\n\n"
            "👤 Ashakert' **{student}**\n"
            "👥 Khmb' **{group}**"
        ),
        "add_already":        "ℹ️ «{student}» ashakerty ardem gtanvum e «{group}» khmbi mej:",
        "add_error":          "❌ Sxal tegi unecav «{student}» ashakerty «{group}» khmbi mej avelajnelu:\n`{msg}`",

        # ── Задачи (tasks) ────────────────────────────────────────────
        "task_added":         "Arajadrankhy avelajvac e:",
        "task_empty":         "Arajadrankhneri tsanky datar e:",
        "task_header":        "📝 **Arajadrankhneri tsank:**\n\n",
        "task_done_cb":       "✅ Task{n} katarva e:",
        "task_not_found_cb":  "❌ Task{n} char gtanvec kam ardem katarva e:",
        "task_all_done":      "🎉 Bolor arajadrankhnery katarvac en:",

        # ── Общие ─────────────────────────────────────────────────────
        "no_db":              "Baza'n miacvac che (POSTGRES_URL):",
        "crm_error":          "❌ Sxal' Alfa CRM-i het kap che:",
        "searching":          "🔄 Patrvasum em...",
        "loading":            "🔄 Bertnum em...",

        # ── /prob / /proball ───────────────────────────────────────────
        "prob_no_schedule": (
            "⚠️ **{loc}** — Pordznakan daseri arazhnagrery nshvac chi:\n"
            "Khndrum enq khetakel vcharneri bazhni:"
        ),
        "no_prob_today":      "Aysor pordznakan daser chka:",
    },

    "ru": {
        # ── Локация (/branch) ──────────────────────────────────────────
        "location_set":       "✅ Локация изменена: **{name}**",
        "location_invalid":   "❌ Неизвестная локация: `{code}`\nИспользуйте: `gn`, `k`, `s`",
        "location_current":   "📍 Активная локация: **{name}**\n\nВыбрать:",
        "location_choose":    "Выберите локацию:",

        # ── Язык (/language) ──────────────────────────────────────────
        "language_set":       "✅ Язык изменён",
        "language_choose":    "Выберите язык:",

        # ── Платёж (process_payment) ──────────────────────────────────
        "payment_searching":  "🔄 Ищу в Alfa CRM...",
        "payment_not_found":  "❌ Лид или клиент с номером {phone} не найден:",
        "payment_wrong_loc": (
            "❌ Найден «{name}», но он не из локации «{loc}»:\n"
            "Для подтверждения платежа отправьте CRM-ссылку на карточку:"
        ),
        "payment_success":    "✅ Платёж зарегистрирован в CRM и ДДС ({name}):\n\n{text}",
        "payment_error":      "❌ Ошибка при создании платежа в CRM:",
        "payment_pending": (
            "❌ Студент не найден в Alfa CRM:\n"
            "Для подтверждения платежа отправьте CRM-ссылку на карточку:"
        ),

        # ── /addprob ──────────────────────────────────────────────────
        "addprob_searching":  "🔄 Ищу...",
        "addprob_not_found":  "❌ Лид или клиент с номером {phone} не найден:",
        "addprob_no_lesson":  "❌ Пробный урок «{lesson}» в указанное время не найден ({dt}):",
        "addprob_added": (
            "✅ **Успешно добавлен!**\n\n"
            "👤 **Студент:** {student}\n"
            "📚 **Урок:** Пробный {lesson}\n"
            "📅 **Время:** {dt}\n"
            "📍 **Локация:** {loc}"
        ),
        "addprob_already":    "⚠️ Студент ({name}) уже записан на этот урок:",
        "addprob_error":      "❌ Ошибка при добавлении на урок: {msg}",

        # ── /add (добавить студента в группу) ─────────────────────────
        "add_no_prefix_grp": (
            "⚠️ **Группа «{group}» не имеет префикса «{prefix}»!**\n\n"
            "Добавление заблокировано: Добавьте «{prefix}» в начало имени "
            "группы в Alfa CRM (пример: `{prefix} | {group}`) и повторите команду:"
        ),
        "add_no_prefix_std": (
            "⚠️ **Студент «{student}» не имеет префикса «{prefix}»!**\n\n"
            "Добавление заблокировано: Добавьте «{prefix}» в начало имени "
            "студента в Alfa CRM (пример: `{prefix} | {student}`) и повторите команду:"
        ),
        "add_success": (
            "✅ **Успешно добавлен!**\n\n"
            "👤 Студент: **{student}**\n"
            "👥 Группа: **{group}**"
        ),
        "add_already":        "ℹ️ Студент «{student}» уже находится в группе «{group}»:",
        "add_error":          "❌ Ошибка при добавлении «{student}» в группу «{group}»:\n`{msg}`",

        # ── Задачи (tasks) ────────────────────────────────────────────
        "task_added":         "Задача добавлена!",
        "task_empty":         "Список задач пуст:",
        "task_header":        "📝 **Список задач:**\n\n",
        "task_done_cb":       "✅ Task{n} выполнен:",
        "task_not_found_cb":  "❌ Task{n} не найден или уже выполнен:",
        "task_all_done":      "🎉 Все задачи выполнены:",

        # ── Общие ─────────────────────────────────────────────────────
        "no_db":              "База не подключена (POSTGRES_URL):",
        "crm_error":          "❌ Ошибка подключения к Alfa CRM:",
        "searching":          "🔄 Ищу...",
        "loading":            "🔄 Загружаю...",

        # ── /prob / /proball ───────────────────────────────────────────
        "prob_no_schedule": (
            "⚠️ **{loc}** — Расписание пробных уроков не настроено:\n"
            "Обратитесь к администратору:"
        ),
        "no_prob_today":      "Сегодня пробных уроков нет:",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    """
    Возвращает переведённую строку по ключу и языку.
    При отсутствии ключа — возвращает сам ключ (не падает).
    Примеры:
        t("location_set", "ru", name="Комитас")  → "✅ Локация изменена: **Комитас**"
        t("task_added",   "hy")                  → "Arajadrankhy avelajvac e:"
    """
    text: str = STRINGS.get(lang, STRINGS["hy"]).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text
