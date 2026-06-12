"""Provides a single function which helps process datelines."""

import re

# Defines various spellings of each month in the Gregorian calendar used in the dataset. This is not meant to be
# a complete list, but it should cover a majority of cases.
MONTH_NAMES = {
    1: [
        'january',
        'jany',
        'janvier',
        'janry',
        'jan',
        'jay',
        'januarii',
        'jnry',
        'janr',
        'janvr',
        'janvier',
        'janv',
    ],
    2: [
        'february',
        'febry',
        'feby',
        'feb',
        'febr',
        'febbio',
        'fevrier',
        'februar',
        'fevr',
        'febre',
        'febuy',
    ],
    3: [
        'march',
        'mars',
        'mar',
        'martii',
        'marz',
    ],
    4: [
        'april',
        'avril',
        'apl',
        'ap',
        'aprill',
        'apr',
    ],
    5: [
        'may',
        'mai',
    ],
    6: [
        'june',
        'juin',
        'jun',
    ],
    7: [
        'july',
        'jully',
        'julliet',
        'jlle',
        'juilt',
        'juin',
        'jullett',
    ],
    8: [
        'august',
        'aug',
        'augt',
        'augst',
        'aout',
        'aoust',
        'aug\'t',
        'agt',
    ],
    9: [
        'september',
        'septr',
        'sepbr',
        'sepber',
        'sep',
        'septemr',
        'sept',
        'sepr',
        'sep\'r',
        '7bre',
        '7br',
        '7ber',
        'sepre',
        'septe',
        'septre',
        'septembre',
    ],
    10: [
        'october',
        '8bre',
        'oct',
        'octr',
        'octob',
        'octo',
        'octor',
        'octobre',
        'occtobre',
        'octobr',
        'd\'octobre',
        'octobe',
        'ocr',
        'octbr',
    ],
    11: [
        'november',
        'nover',
        'novr',
        'nov',
        'nbre',
        'novembr',
        '9bre',
        '9ber',
        '9vembre',
        'novem',
        'novembre',
        'novemr',
        'nvbr',
        'nov\'r',
    ],
    12: [
        'december',
        'dec',
        'decr',
        'xbre',
        'ecre',
        'dece',
        'decbre',
        'decembre',
        'decemr',
        'decem',
        'decbr',
        'dec\'r',
        'dcmer',
        'dbre',
        'dcr',
        'decer',
        'decemb',
        'decembr',
    ]
}
ALL_MONTH_NAMES = [name for names in MONTH_NAMES.values() for name in names]
OTHER_TIME_WORDS = [
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday',
    'morning',
    'midday',
    'afternoon',
    'evening',
    'night',
]

# A regex pattern matching the start of a date indication in a dateline.
START_OF_DATE_PATTERN = re.compile(
    r'[0-9]+|' + '|'.join(rf'\b{re.escape(name)}\b' for name in ALL_MONTH_NAMES + OTHER_TIME_WORDS),
    flags=re.IGNORECASE
)


def get_name_from_dateline(dateline: str) -> str:
    """
    Attempt to extract the name of the place within a dateline.  This doesn't work 100% of the time but is generally
    good at removing dates.
    """
    parts = [part.strip() for part in START_OF_DATE_PATTERN.split(dateline)]
    return parts[0] or parts[-1]
