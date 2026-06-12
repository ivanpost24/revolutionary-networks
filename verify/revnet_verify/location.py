"""Utility functions for dealing with the Location column in Revolutionary Networks data."""


import re


# A regex pattern for Location strings where the first group contains the state or country containing the location.
STATE_OR_COUNTRY_PATTERN = re.compile(r'.*\[(.+)]$')


def get_state_or_country(loc: str) -> str | None:
    """Get the state or country string from the given Revolutionary Networks location string."""
    if not isinstance(loc, str):
        return None
    match = STATE_OR_COUNTRY_PATTERN.match(loc)
    if match is None:
        return None
    else:
        return match.group(1)


# The expected country codes for a given administrative location based on its canonical spelling.
CORRESPONDING_COUNTRY_CODES = {
    'Conn.': ['US'],
    'Del.': ['US'],
    'Fla.': ['US'],
    'Ga.': ['US'],
    'Ky.': ['US'],
    'Louisiana': ['US'],
    'Mass.': ['US'],
    'Md.': ['US'],
    'Me.': ['US'],
    'N.C.': ['US'],
    'N.H.': ['US'],
    'N.J.': ['US'],
    'N.Y.': ['US'],
    'Pa.': ['US'],
    'Va.': ['US'],
    'R.I.': ['US'],
    'S.C.': ['US'],
    'Tenn.': ['US'],
    'W.Va.': ['US'],
    'Vt.': ['US'],
    'Illinois Country': ['US'],
    'near Dobbs Ferry': ['US'],
    'now Maine': ['US'],
    'Virgin Islands': ['VG', 'VI', 'US', 'GB'],
    'Austria': ['AT'],
    'Belgium': ['BE'],
    'Bohemia': ['CZ'],
    'Canada': ['CA'],
    'Canary Islands': ['ES'],
    'Cuba': ['CU'],
    'Denmark': ['DK'],
    'Egypt': ['EG'],
    'England': ['GB'],
    'France': ['FR'],
    'Germany': ['DE'],
    'Guadeloupe': ['GP'],
    'Haiti': ['HT'],
    'Ireland': ['IE', 'GB'],
    'Italy': ['IT'],
    'Jamaica': ['JM'],
    'Martinique': ['MQ'],
    'Netherlands': ['NL'],
    'Norway': ['NO'],
    'Poland': ['PL'],
    'Portugal': ['PT'],
    'Russia': ['RU'],
    'Scotland': ['GB'],
    'Spain': ['ES'],
    'Suriname': ['SR'],
    'Sweden': ['SE'],
    'Switzerland': ['CH'],
    'Tunisia': ['TN'],
    'Wales': ['GB'],
}


def get_country_code(state_or_country: str) -> list[str]:
    """Get possible country codes given the state/country part of a Revolutionary Networks location string."""
    return CORRESPONDING_COUNTRY_CODES.get(state_or_country, [])


def get_location_name(loc: str) -> str:
    """Get the primary location (city or county) name from the given Revolutionary Networks location string."""
    return loc.split('[')[0].strip().split(', ')[0]
