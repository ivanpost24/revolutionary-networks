import argparse
import shutil
import sys
from collections.abc import Sequence
from functools import partial

import numpy as np
import pandas as pd

from . import progress, PROGRAM_DIR
from .geonames import (
    get_geonames,
    get_geonames_country_codes,
    get_geonames_admin1_info,
    get_geonames_admin2_info,
)
from .progress import spinning_cursor
from .rotunda import get_revnet_data, get_hierarchy_string
from .textwrapping import wrap_text
from .verifications import verifications

MAIN_DESCRIPTION = '''\
revnet-verify allows users to find potential errors in the revolutionary-networks dataset.

When executed with the "check" command, the program will examine the provided Revolutionary Networks data file for
issues.  These will all be logged to the standard output, with the spreadsheet row, document ID, a string identifying
the type of issue, and an explanatory message.  The program ignores rows for which the "verified" column, if it exists,
is TRUE.  Columns which do not have a location entry are reported at the top of the log and also ignored.  You can
disable certain types of issues with the -d flag; use the "list" command to get the issue types or the "describe"
command to get the description of a specific issue.

The program caches large data files downloaded from the Geonames website locally in the $HOME/.revnet-verify directory. 
The directory is automatically created the first time the program is executed.  The download will automatically occur
the first time you run the "check" command and requires an Internet connection.  You can also trigger the file download
with the "download" command and clear the download with the "cleardata" command.

If you want more details on any command, run "revnet-verify [command] --help."'''


CHECK_DESCRIPTION = '''\
The "check" command is the primary command, which actually checks a Revolutionary Networks data file for potential
problems.

The program will examine the provided Revolutionary Networks data file for issues.  These will all be logged to the
standard output, with the spreadsheet row, document ID, a string identifying the type of issue, and an explanatory
message. The program ignores rows which have been marked as verified unless the -a flag is specified.  Rows which do not
have a location entry are ignored and reported at the top of the log.  You can disable certain types of issues with the
-d flag.

Also, the first time that this command is run, the program will download data from the Geonames database.  This download
can take a while, and a busy indicator will be printed to the standard error file to indicate what is happening.  The
result is automatically cached on disk, but you can force the program to reach out to the Geonames database with the -f
flag.  In either case, an Internet connection is required.

You will likely want to redirect the standard output file to a file on disk using your shell's functionality.'''

LIST_DESCRIPTION = '''\
The "list" command prints all the issue types, each on their own line, to the standard output file.'''

DESCRIBE_DESCRIPTION = '''\
The "describe" command gets a textual description of a specific issue type and prints it to the standard output file.'''

FIX_GEONAMES_DESCRIPTION = '''\
The "fix-geonames" command fixes the Geonames metadata columns in the provided Revolutionary Networks data file.

The program will print to the standard output a CSV document where the "coordinates", "latitude", "longitude",
"country_code", "country_name", "admin1", "admin2", and "hierarchy" columns are updated to match the Geonames dataset. 
It ignores rows which do not have an entry in the "geonameId" column.

Like the "check" command, the first time that this command is run, the program will download data from the Geonames
database.  This download can take a while, and a busy indicator will be printed to the standard error file to indicate
what is happening.  The result is automatically cached on disk, but you can force the program to reach out to the
Geonames database with the -f flag.  In either case, an Internet connection is required.

You will likely want to redirect the standard output file to a file on disk using your shell's functionality.  Do NOT
redirect to the same file which you are modifying.'''

DOWNLOAD_DESCRIPTION = '''\
The "download" command downloads necessary data from the Geonames database and stores it such that the program can
quickly read it for future executions.

The necessary data is split across several files on the Geonames file server, and it downloads them one at a time.  A
busy indicator is printed to the standard error file by default, but this can be disabled if necessary.

Once the data is processed and merged, it will be stored in a single Parquet table file in the $HOME/.revnet-verify
directory.  If this file already exists, then the download will not occur unless the -f flag is provided.'''

CLEARDATA_DESCRIPTION = '''\
The "cleardata" command deletes the $HOME/.revnet-verify directory created to cache data downloaded from the Geonames
database.'''


GEONAMES_CACHE_PATH = PROGRAM_DIR / 'all_geonames.parquet'


def get_all_geonames_data(force: bool = False, cache: bool = True) -> pd.DataFrame:
    if GEONAMES_CACHE_PATH.exists() and not force:
        with spinning_cursor('Loading all Geonames data'):
            data = pd.read_parquet(GEONAMES_CACHE_PATH)
    else:
        geonames_data = get_geonames(force=force, cache=False)
        country_code_info = get_geonames_country_codes(force=force, cache=False)[['ISO', 'Country']].rename(columns={
            'ISO': 'country code',
            'Country': 'country name',
        })
        admin1_info = get_geonames_admin1_info(force=force, cache=False)[['code', 'name']].rename(columns={
            'code': 'admin1_key',
            'name': 'admin1 name',
        })
        admin2_info = get_geonames_admin2_info(force=force, cache=False)[['code', 'name']].rename(columns={
            'code': 'admin2_key',
            'name': 'admin2 name',
        })
        with spinning_cursor('Merging Geonames data'):
            data = geonames_data.merge(country_code_info, on='country code', how='left')
            data['admin1_key'] = data.apply(
                lambda x: f'{x['country code']}.{x['admin1 code']}', axis='columns'
            )
            data = data.merge(admin1_info, on='admin1_key', how='left')
            data.drop(columns=['admin1_key'], inplace=True)
            data['admin2_key'] = data.apply(
                lambda x: f'{x['country code']}.{x['admin1 code']}.{x['admin2 code']}', axis='columns'
            )
            data = data.merge(admin2_info, on='admin2_key', how='left')
            data.drop(columns=['admin2_key'], inplace=True)
            data.index = geonames_data.index
            if cache:
                data.to_parquet(GEONAMES_CACHE_PATH)
    return data


def verify(
    path_to_data: str,
    ignore_verified: bool = True,
    disable: Sequence[str] = (),
    force: bool = False,
    busy: bool = True
) -> None:
    """Subcommand which checks the validity of the Rotunda data file at the given path or URL."""
    progress.enabled = busy
    data = get_revnet_data(path_to_data)
    data_with_geonames = data.dropna(subset=['geonameId'])
    data_with_geonames['geonameId'] = data_with_geonames['geonameId'].astype(np.uint64)
    documents_without_geonames = data.loc[
        data.index.difference(data_with_geonames.index),
        'DocumentID'
    ]
    if len(documents_without_geonames) > 0:
        print(
            f'There are {len(documents_without_geonames)} documents without associated Geonames entities.',
            'They will be ignored and are as follows:',
            ', '.join(documents_without_geonames)
        )

    geonames_data = get_all_geonames_data(force=force)

    merged_data = pd.merge(
        data_with_geonames,
        geonames_data,
        left_on='geonameId',
        right_index=True,
        how='left',
        indicator=True,
        suffixes=('', '_geonames')
    )
    if 'verified' in merged_data.columns and ignore_verified:
        merged_data = merged_data[~merged_data['verified']]

    if disable is not None:
        disable = set(name.lower() for name in disable)
        if not disable.issubset(verifications.keys()):
            invalid_issue_types = disable - verifications.keys()
            print('unrecognized issue types:', ', '.join(invalid_issue_types), file=sys.stderr)
            sys.exit(1)
        verifications_used = {name: verifications[name] for name in verifications.keys() - disable}
    else:
        verifications_used = verifications

    for index, entry in merged_data.iterrows():
        for verification_name, verification_func in verifications_used.items():
            if (error := verification_func(entry)) is not None:
                print(f'row {index + 2} [{entry['DocumentID']}, {verification_name}]: {error}')


def list_issue_types() -> None:
    print('\n'.join(verifications.keys()))


def describe(issue_type: str) -> None:
    if issue_type not in verifications:
        print(f'unrecognized issue type: {issue_type}', file=sys.stderr)
        sys.exit(1)
    elif verifications[issue_type].__doc__ is None:
        print(f'no description found for issue type "{issue_type}"', file=sys.stderr)
        sys.exit(1)
    else:
        print(wrap_text(verifications[issue_type].__doc__, width=shutil.get_terminal_size().columns))


def fix_geonames(path_to_data: str, force: bool = False, busy: bool = True) -> None:
    progress.enabled = busy
    data = get_revnet_data(path_to_data)
    data_with_geonames = data.dropna(subset=['geonameId'])
    data_with_geonames['geonameId'] = data_with_geonames['geonameId'].astype(np.uint64)

    geonames_data = get_all_geonames_data(force=force)

    merged_data = pd.merge(
        data_with_geonames,
        geonames_data,
        left_on='geonameId',
        right_index=True,
        how='left',
        indicator=True,
        suffixes=('', '_geonames')
    )

    merged_data['coordinates'] = merged_data.apply(
        lambda entry: f'{entry['latitude_geonames']:.5f}, {entry['longitude_geonames']:.5f}',
        axis='columns'
    )
    merged_data['latitude'] = merged_data['latitude_geonames']
    merged_data['longitude'] = merged_data['longitude_geonames']
    merged_data['country_code'] = merged_data['country code']
    merged_data['country_name'] = merged_data['country name']
    merged_data['admin1'] = merged_data['admin1 name']
    merged_data['admin2'] = merged_data['admin2 name']
    merged_data['hierarchy'] = merged_data.apply(get_hierarchy_string, axis='columns')

    merged_data[data.columns].to_csv(sys.stdout, index=False)


def download(force: bool = False) -> None:
    if GEONAMES_CACHE_PATH and not force:
        print('Geonames data is already cached, use -f/--force to override')
    else:
        get_all_geonames_data(force=force)


def clear_program_data() -> None:
    """Deletes the program directory."""
    shutil.rmtree(PROGRAM_DIR)


def main() -> None:
    text_wrapper = partial(wrap_text, width=shutil.get_terminal_size().columns)
    parser = argparse.ArgumentParser(
        description=text_wrapper(MAIN_DESCRIPTION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.suggest_on_error = True
    subparsers = parser.add_subparsers(required=True)

    check_parser = subparsers.add_parser(
        'check',
        description=text_wrapper(CHECK_DESCRIPTION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Perform verifications on a Rotunda dataset file',
    )
    check_parser.add_argument(
        'path_to_data',
        help='Path to a CSV file containing Rotunda data',
    )
    check_parser.add_argument(
        '-a',
        '--all',
        dest='ignore_verified',
        action='store_false',
        help='Check all dataset entries, even ones which are marked as verified',
    )
    check_parser.add_argument(
        '-d',
        '--disable',
        dest='disable',
        action='append',
        help='Disable a verification on this run',
    )
    check_parser.add_argument(
        '-f',
        '--fetch',
        dest='force',
        action='store_true',
        help='Force fetching Geonames data from the server even if the data is already cached',
    )
    check_parser.add_argument(
        '--nobusy',
        dest='busy',
        action='store_false',
        help='Disable the busy indicators printed to the standard error file'
    )
    check_parser.set_defaults(func=verify)

    list_parser = subparsers.add_parser(
        'list',
        description=text_wrapper(LIST_DESCRIPTION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='List all issue types'
    )
    list_parser.set_defaults(func=list_issue_types)

    describe_parser = subparsers.add_parser(
        'describe',
        description=text_wrapper(DESCRIBE_DESCRIPTION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Describe an issue type'
    )
    describe_parser.add_argument(
        'issue_type',
        help='Issue type to describe'
    )
    describe_parser.set_defaults(func=describe)

    fix_geonames_parser = subparsers.add_parser(
        'fix-geonames',
        description='',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Fix the Geonames metadata columns in the dataset'
    )
    fix_geonames_parser.add_argument(
        'path_to_data',
        help='Path to a CSV file containing Rotunda data',
    )
    fix_geonames_parser.add_argument(
        '-f',
        '--fetch',
        dest='force',
        action='store_true',
        help='Force fetching Geonames data from the server even if the data is already cached',
    )
    fix_geonames_parser.add_argument(
        '--nobusy',
        dest='busy',
        action='store_false',
        help='Disable the busy indicators printed to the standard error file'
    )
    fix_geonames_parser.set_defaults(func=fix_geonames)

    download_parser = subparsers.add_parser(
        'download',
        description=text_wrapper(DOWNLOAD_DESCRIPTION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Download the needed Geonames data'
    )
    download_parser.add_argument(
        '-f',
        '--force',
        dest='force',
        action='store_true',
        help='Force fetching Geonames data even if the data is already cached',
    )
    download_parser.set_defaults(func=download)

    cleardata_parser = subparsers.add_parser(
        'cleardata',
        description=text_wrapper(CLEARDATA_DESCRIPTION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Clear the program directory ($HOME/.revnet-verify)'
    )
    cleardata_parser.set_defaults(func=clear_program_data)

    args = parser.parse_args()
    command = args.func
    vars(args).pop('func')
    command(**vars(args))


if __name__ == '__main__':
    main()
