"""Module for reading """

from pathlib import Path

import numpy as np
import pandas as pd

from .progress import spinning_cursor


@spinning_cursor('Loading Revolutionary Networks data')
def get_revnet_data(path: str | Path) -> pd.DataFrame:
    """
    Get Revolutionary Networks data at the provided path and return it in a DataFrame.

    The DataFrame columns are as follows::

       DocumentID: ID of the document in the Rotunda database
       Title: title of the document
       Author: author(s) of the document
       Recipient: recipient(s) of the document if known
       Date: date of the document
       Publication: ID of the Rotunda digital edition where the document is found
       Founders Online: URL to the version of this document on Founders Online, if it is published there
       Rotunda: URL to the version of this document in the Rotunda digital editions
       authorIDs: ID(s) for the document's author(s)
       recipientIDs: ID(s) for the document's recipient(s)
       OrigDateline: digitally transcribed Dateline from the digital edition of the document
       Location: location extracted from the dateline or surrounding context, in the format
          `City/Entity, County [State/Country]` or `County/Entity [State/Country]`. Data from the revised_location
          column is also merged into this one.
       geonameId: ID of the corresponding Geoname entity for the location
       coordinates: string for the location
       latitude: latitude of the location from Geonames
       longitude: longitude of the location from Geonames
       country_code: ISO 3166 two-letter country code of the location from Geonames
       country_name: name of the country of the location from Geonames
       admin1: first-order administrative division containing the location from Geonames
       admin2: second-order administrative division containing the location from Geonames
       hierarchy: list of administrative divisions in increasing order, separated by " > "

    :param path: Path or URL to the Rotunda data file.
    :return: A DataFrame with the columns listed above from the Rotunda data at the given path or URL.
    """
    data = pd.read_csv(
        path,
        dtype={
            'OrigDateline': str,
            'geonameId': pd.UInt64Dtype(),
            'coordinates': str,
            'latitude': np.float64,
            'longitude': np.float64,
        }
    )
    if 'revised_location' in data.columns:
        data.loc[pd.notna(data['revised_location']), 'Location'] = (
            data.loc[pd.notna(data['revised_location']), 'revised_location']
        )
        data.drop(columns=['revised_location'], inplace=True)
    data['Date'] = pd.to_datetime(data['Date'], dayfirst=True, unit='D')
    return data


def get_hierarchy_string(entry: pd.Series) -> str | float:
    if pd.notna(country_name := entry['country_name']):
        if pd.notna(admin1 := entry['admin1']):
            if pd.notna(admin2 := entry['admin2']):
                return f'{country_name} > {admin1} > {admin2}'
            else:
                return f'{country_name} > {admin1}'
        else:
            return country_name
    else:
        return np.nan
