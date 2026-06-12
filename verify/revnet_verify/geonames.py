"""Functions for fetching Geonames data."""

import numpy as np
import pandas as pd

from . import PROGRAM_DIR
from .progress import spinning_cursor


@spinning_cursor('Loading Geonames database')
def get_geonames(force: bool = False, cache: bool = True) -> pd.DataFrame:
    """
    Get a DataFrame containing the entire Geonames location database. This is a long-running operation and may require
    an Internet connection.

    See https://download.geonames.org/export/dump/readme.txt for the names of each column.

    This method will, by default, cache the database in the user directory to avoid contacting the servers every single
    time. It will also fetch from this cache by default.

    :param force: If `True`, then forces the function to fetch the database from the Internet, ignoring any cached
       version (default: `False`).
    :param cache: If `True`, cache the database in the program directory (default: `True`).
    :return: A DataFrame containing the Geonames location database.
    """
    cached_file = PROGRAM_DIR / 'geonames.parquet'
    if cached_file.exists() and not force:
        data = pd.read_parquet(cached_file)
    else:
        data = pd.read_csv(
            'https://download.geonames.org/export/dump/allCountries.zip',
            delimiter='\t',
            index_col=0,
            header=None,
            names=[
                'geonameid',
                'name',
                'asciiname',
                'alternatenames',
                'latitude',
                'longitude',
                'feature class',
                'feature code',
                'country code',
                'cc2',
                'admin1 code',
                'admin2 code',
                'admin3 code',
                'admin4 code',
                'population',
                'elevation',
                'dem',
                'timezone',
                'modification date'
            ],
            dtype={
                'geonameid': np.uint64,
                'name': str,
                'asciiname': str,
                'alternatenames': str,
                'feature class': str,
                'feature code': str,
                'country code': str,
                'cc2': str,
                'admin1 code': str,
                'admin2 code': str,
                'admin3 code': str,
                'admin4 code': str,
                'timezone': str
            },
        )
        data['alternatenames'] = data['alternatenames'].map(
            lambda x: np.array(x.split(',') if pd.notna(x) else [], dtype=np.str_)
        )
        if cache:
            data.to_parquet(cached_file)
    return data


@spinning_cursor('Loading country code information')
def _fetch_geonames_country_codes(force: bool = False, cache: bool = True) -> pd.DataFrame:
    cached_file = PROGRAM_DIR / 'country_codes.parquet'
    if cached_file.exists() and not force:
        data = pd.read_parquet(cached_file)
    else:
        data = pd.read_csv(
            'https://download.geonames.org/export/dump/countryInfo.txt',
            delimiter='\t',
            comment='#',
            names=[
                'ISO',
                'ISO3',
                'ISO-Numeric',
                'fips',
                'Country',
                'Capital',
                'Area(in sq km)',
                'Population',
                'Continent',
                'tld',
                'CurrencyCode',
                'CurrencyName',
                'Phone',
                'Postal Code Format',
                'Postal Code Regex',
                'Languages',
                'geonameid',
                'neighbours',
                'EquivalentFipsCode',
            ],
        )
        if cache:
            data.to_parquet(cached_file)
    return data


_geonames_country_codes = pd.DataFrame()


def get_geonames_country_codes(force: bool = False, cache: bool = True) -> pd.DataFrame:
    """
    Get a DataFrame containing information about country codes used in the Geonames database. This is a long-running
    operation and may require an Internet connection.

    The function downloads the data from https://download.geonames.org/export/dump/countryInfo.txt.

    This method will, by default, cache the database in the user directory to avoid contacting the servers every single
    time. It will also fetch from this cache by default.

    :param force: If `True`, then forces the function to fetch the data from the Internet, ignoring any cached
       version (default: `False`).
    :param cache: If `True`, cache the data in the program directory (default: `True`).
    :return: A DataFrame containing information about country codes used in the Geonames database.
    """
    global _geonames_country_codes
    if _geonames_country_codes.empty or force:
        _geonames_country_codes = _fetch_geonames_country_codes(force=force, cache=cache)
    return _geonames_country_codes


@spinning_cursor('Loading first-order administrative division information')
def _fetch_geonames_admin1_info(force: bool = False, cache: bool = True) -> pd.DataFrame:
    cached_file = PROGRAM_DIR / 'admin1_info.parquet'
    if cached_file.exists() and not force:
        data = pd.read_parquet(cached_file)
    else:
        data = pd.read_csv(
            'https://download.geonames.org/export/dump/admin1CodesASCII.txt',
            delimiter='\t',
            names=[
                'code',
                'name',
                'name ascii',
                'geonameid',
            ],
        )
        if cache:
            data.to_parquet(cached_file)
    return data


_geonames_admin1_info = pd.DataFrame()


def get_geonames_admin1_info(force: bool = False, cache: bool = True) -> pd.DataFrame:
    """
    Get a DataFrame containing information about first-order administrative divisions used in the Geonames database.
    This is a long-running operation and may require an Internet connection.

    The function downloads the data from https://download.geonames.org/export/dump/admin1CodesASCII.txt and the
    columns are specified in https://download.geonames.org/export/dump/readme.txt.

    This method will, by default, cache the database in the user directory to avoid contacting the servers every single
    time. It will also fetch from this cache by default.

    :param force: If `True`, then forces the function to fetch the database from the Internet, ignoring any cached
       version (default: `False`).
    :param cache: If `True`, cache the database in the program directory (default: `True`).
    :return: A DataFrame containing the information about first-order administrative divisions used in the Geonames
       database.
    """
    global _geonames_admin1_info
    if _geonames_admin1_info.empty or force:
        _geonames_admin1_info = _fetch_geonames_admin1_info(force=force, cache=cache)
    return _geonames_admin1_info


@spinning_cursor('Loading second-order administrative division information')
def _fetch_geonames_admin2_info(force: bool = False, cache: bool = True) -> pd.DataFrame:
    cached_file = PROGRAM_DIR / 'admin2_info.parquet'
    if cached_file.exists() and not force:
        data = pd.read_parquet(cached_file)
    else:
        data = pd.read_csv(
            'https://download.geonames.org/export/dump/admin2Codes.txt',
            delimiter='\t',
            comment='#',
            names=[
                'code',
                'name',
                'name ascii',
                'geonameid',
            ],
        )
        if cache:
            data.to_parquet(cached_file)
    return data


_geonames_admin2_info = pd.DataFrame()


def get_geonames_admin2_info(force: bool = False, cache: bool = True) -> pd.DataFrame:
    """
    Get a DataFrame containing information about second-order administrative divisions used in the Geonames database.
    This is a long-running operation and may require an Internet connection.

    The function downloads the data from https://download.geonames.org/export/dump/admin2Codes.txt and the columns are
    specified in https://download.geonames.org/export/dump/readme.txt.

    This method will, by default, cache the database in the user directory to avoid contacting the servers every single
    time. It will also fetch from this cache by default.

    :param force: If `True`, then forces the function to fetch the database from the Internet, ignoring any cached
       version (default: `False`).
    :param cache: If `True`, cache the database in the program directory (default: `True`).
    :return: A DataFrame containing the information about first-order administrative divisions used in the Geonames
       database.
    """
    global _geonames_admin2_info
    if _geonames_admin2_info.empty or force:
        _geonames_admin2_info = _fetch_geonames_admin2_info(force=force, cache=cache)
    return _geonames_admin2_info
