# api/locations.py
# Централизованная конфигурация локаций RobixLab
# ONE CRM branch (branch_id=1), THREE locations (location_id).

LOCATIONS = {
    "GN": {
        "code": "GN",
        "name": "Гарегин Нжде",
        "crm_prefix": "G.N",
        "location_id": 5,
        "branch_id": 1,
        "rooms": {"lego": 33, "makeblock": 34},
        "accounts": {"cash": 5, "terminal": 6, "card": 2},
        "sheets_tab": "Оплаты Манташяна",
    },
    "K": {
        "code": "K",
        "name": "Комитас",
        "crm_prefix": "K",
        "location_id": 1,
        "branch_id": 1,
        "rooms": {"lego": 30, "makeblock": 31},
        "accounts": {"cash": 1, "terminal": 3, "card": 2},
        "sheets_tab": "Оплаты Комитаса",
    },
    "S": {
        "code": "S",
        "name": "Саят-Нова",
        "crm_prefix": "T.M",
        "location_id": 2,
        "branch_id": 1,
        "rooms": {"lego": None, "makeblock": None},
        "accounts": {"cash": 7, "terminal": 8, "card": 2},
        "sheets_tab": "Оплаты Кентрон",
    },
}

LOCATION_ALIASES = {
    "gn": "GN",
    "g.n": "GN",
    "нжде": "GN",
    "garegin": "GN",
    "garegin nzhde": "GN",
    "k": "K",
    "комитас": "K",
    "komitas": "K",
    "s": "S",
    "саят": "S",
    "sayat": "S",
    "t.m": "S",
    "тм": "S",
    "sayat-nova": "S",
    "саят-нова": "S",
}

DEFAULT_LOCATION = "GN"


def get_location(code: str):
    """Возвращает конфиг локации по коду (GN, K, S). None если не найдено."""
    return LOCATIONS.get(code)


def resolve_alias(raw: str):
    """Парсит пользовательский ввод (/branch gn|k|s) и возвращает код локации или None."""
    return LOCATION_ALIASES.get(raw.lower().strip())
