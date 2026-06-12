"""Verification functions."""

import re
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import TypeAlias

import numpy as np
import pandas as pd

from .dateline import get_name_from_dateline
from .featurecode import get_feature_key, get_feature_code_name
from .location import get_state_or_country, get_country_code, get_location_name

Verifier: TypeAlias = Callable[[pd.Series], str | None]

ALPHA_PATTERN = re.compile(r'\w{2,}')

verifications: dict[str, Verifier] = {}


def register(name: str) -> Callable[[Verifier], Verifier]:
    """
    Decorator factory which registers a verification function to the registry.

    A verification function must take a pandas Series as its only positional argument containing the row to check and
    return either None (on success) or an error message (on failure).

    So that the "describe" command is useful, you should also provide a docstring.

    :param name: Name of the verification function. These are printed to the standard output so the user can filter by
       issue type, and a user can disable this function by specifying this name on the command line.
    :return: A decorator which registers the provided verification function to the registry.
    """
    if name in verifications:
        raise ValueError(f'Verification {name} already registered')

    def decorator(func: Verifier) -> Verifier:
        verifications[name] = func
        return func

    return decorator


@register('coordinates-column-matches')
def verify_coordinates_column_matches(entry: pd.Series) -> str | None:
    """Verify that data in the coordinates column matches data in the latitude and longitude columns."""
    latitude = entry['latitude']
    longitude = entry['longitude']
    coordinate_string = entry['coordinates']
    if (
        f'{latitude:.4f}, {longitude:.4f}' == coordinate_string
        or f'{latitude:.5f}, {longitude:.5f}' == coordinate_string
    ):
        return None
    else:
        return f'coordinates {coordinate_string} do not match latitude {latitude:.5f} and longitude {longitude:.5f}'


@register('geonames-id')
def verify_geonames_id(entry: pd.Series) -> str | None:
    """
    Verify that the associated Geonames IDs actually exist in the Geonames database.  This issue can also occur if you
    reference a location recently added to the database; consider running with --force.
    """
    if entry['_merge']:
        return None
    else:
        return (f'there is no Geonames entity with ID {entry['geonameId']}. If the entity was recently added to the '
                f'database, please run "revnet-verify cleardata" so the most recent database will be used.')


@register('geonames-feature-code')
def verify_geonames_feature_code(entry: pd.Series) -> str | None:
    """
    Verify that the feature code of the associated Geonames ID makes sense for the dataset.  This verification will not
    flag Geonames entities with the A and P feature classes or S.HSTS or T.ISL.
    """
    if pd.isna(entry['feature class']):
        return None
    feature_key = get_feature_key(
        entry['feature class'],
        entry['feature code'] if pd.notna(entry['feature code']) else None
    )
    if feature_key.startswith('A') or feature_key.startswith('P') or feature_key in ('S.HSTS', 'T.ISL', ):
        return None
    else:
        return f'suspicious feature code "{feature_key}" ({get_feature_code_name(
            entry['feature class'], 
            entry['feature code'] if pd.notna(entry['feature code']) else None
        )}) for associated Geonames entity "{entry['name']}" ({entry['geonameId']})'


@register('recorded-place-name-similar-to-geoname')
def verify_recorded_place_name_similar_to_geoname(
    entry: pd.Series,
    similarity_threshold: float = 0.3
) -> str | None:
    """
    Verify that the recorded place name in the Location column is reasonably similar to the associated Geonames
    entity's name.
    """
    if pd.isna(entry['Location']):
        return None
    geonames: list[str] = [entry['name']] + entry['alternatenames'].astype('str').tolist()
    location = get_location_name(entry['Location'])
    if any(
        location.casefold() in geoname
        or geoname in location.casefold()
        for geoname in map(str.casefold, geonames)
    ):
        return None
    similarity = max(SequenceMatcher(None, location, geoname).ratio() for geoname in geonames)
    if similarity < similarity_threshold:
        return (f'Geonames entity "{geonames[0]}" ({entry['geonameId']}) has no similar name '
                f'to recorded location "{location}"')
    else:
        return None


@register('recorded-place-name-similar-to-dateline')
def verify_recorded_place_name_similar_to_dateline(
    entry: pd.Series,
    similarity_threshold: float = 0.3
) -> str | None:
    """
    Verify that the recorded place name in the Location column is reasonably similar to the associated Geonames
    entity's name.
    """
    if pd.isna(entry['OrigDateline']) or pd.isna(entry['Location']):
        return None
    dateline_name = get_name_from_dateline(entry['OrigDateline'])
    if ALPHA_PATTERN.search(dateline_name) is None:
        return None
    location = get_location_name(entry['Location'])
    similarity = SequenceMatcher(None, location, dateline_name).ratio()
    if similarity < similarity_threshold:
        return f'Recorded place name "{location}" not similar to name "{dateline_name}" extracted from deadline'
    else:
        return None


@register('recorded-country-code-matches-location')
def verify_recorded_country_code_matches_location(entry: pd.Series) -> str | None:
    """
    Verify that the recorded country code in the Location column matches the state or country included in the
    Location column.
    """
    if pd.isna(entry['OrigDateline']) or pd.isna(entry['Location']):
        return None
    country_code = entry['country_code']
    state_or_country = get_state_or_country(entry['Location'])
    if state_or_country is None:
        return None
    expected_codes = get_country_code(state_or_country)
    if expected_codes and country_code in expected_codes:
        return None
    else:
        return (f'recorded country code "{country_code}" does not match location of '
                f'state or country "{state_or_country}"')


@register('recorded-latlong')
def verify_recorded_latlong(entry: pd.Series) -> str | None:
    """
    Verify that the recorded latitude and longitude in the Location column is reasonably similar to the coordinates of
    the associated Geonames entity.
    """
    if (
        np.isclose(entry['latitude'], entry['latitude_geonames'])
        and np.isclose(entry['longitude'], entry['longitude_geonames'])
    ):
        return None
    else:
        return (
            f'recorded coordinates {entry['latitude']}, {entry['longitude']} do not match '
            f'Geoname coordinates {entry['latitude_geonames']}, {entry['longitude_geonames']}'
        )


@register('recorded-country-code')
def verify_recorded_country_code(entry: pd.Series) -> str | None:
    """
    Verify that the recorded country code in the Location column matches the Geonames entity's country.
    """
    if (
        entry['country_code'] == entry['country code']
        or pd.isna(entry['country_code'])
        or pd.isna(entry['country code'])
    ):
        return None
    else:
        return (f'recorded country code "{entry['country_code']}" does not match '
                f'Geonames country code "{entry['country code']}"')


@register('recorded-country-name')
def verify_recorded_country_name(entry: pd.Series) -> str | None:
    """
    Verify that the recorded country name in the Location column matches the Geonames entity's country.
    """
    if (
        entry['country_name'] == entry['country name']
        or pd.isna(entry['country_name'])
        or pd.isna(entry['country name'])
    ):
        return None
    else:
        return (f'recorded country name "{entry['country_name']}" does not match '
                f'Geonames country name "{entry['country name']}"')


@register('recorded-admin1')
def verify_recorded_admin1_name(entry: pd.Series) -> str | None:
    """
    Verify that the recorded first-order administrative division name in the Location column matches the Geonames
    entity's first-order administrative division, if it exists.
    """
    if (
        entry['admin1'] == entry['admin1 name']
        or pd.isna(entry['admin1'])
        or pd.isna(entry['admin1 name'])
    ):
        return None
    else:
        return (f'recorded first-order administrative division name "{entry['admin1']}" does not match '
                f'Geonames first-order administrative division name "{entry['admin1 name']}"')


@register('recorded-admin2')
def verify_recorded_admin2_name(entry: pd.Series) -> str | None:
    """
    Verify that the recorded second-order administrative division name in the Location column matches the Geonames
    entity's second-order administrative division, if it exists.
    """
    if (
            entry['admin2'] == entry['admin2 name']
            or pd.isna(entry['admin2'])
            or pd.isna(entry['admin2 name'])
    ):
        return None
    else:
        return (f'recorded second-order administrative division name "{entry['admin2']}" does not match '
                f'Geonames second-order administrative division name "{entry['admin2 name']}"')


@register('geonames-place-name-similar-to-dateline')
def verify_geonames_place_name_similar_to_dateline(
    entry: pd.Series,
    similarity_threshold: float = 0.3
) -> str | None:
    """
    Verify that the dateline contents of the document are similar to the Geonames entity's name.
    """
    if pd.isna(entry['OrigDateline']):
        return None
    geonames: list[str] = [entry['name']] + entry['alternatenames'].tolist()
    dateline_name = get_name_from_dateline(entry['OrigDateline'])
    if ALPHA_PATTERN.search(dateline_name) is None:
        return None
    similarity = max(SequenceMatcher(None, dateline_name, geoname).ratio() for geoname in geonames)
    if similarity < similarity_threshold:
        return (f'Geonames entity "{geonames[0]}" ({entry['geonameId']}) has no similar name to '
                f'location "{dateline_name}" extracted from dateline')
    else:
        return None
