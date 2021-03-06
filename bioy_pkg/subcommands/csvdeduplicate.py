# This file is part of Bioy
#
#    Bioy is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bioy is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bioy.  If not, see <http://www.gnu.org/licenses/>.

"""Deduplicate any number of csv file with optional column group indexing.
"""

import logging
import pandas
import sys

from bioy_pkg import utils

log = logging.getLogger(__name__)


def build_parser(parser):
    # required inputs
    parser.add_argument(
        'csv',
        nargs='+',
        help='CSV tabular blast file of query and subject hits.')

    # common outputs
    parser.add_argument(
        '-o', '--out', metavar='FILE',
        default=sys.stdout, type=utils.Opener('w'),
        help="Classification results.")

    parser.add_argument(
        '--limit', type=int, help='Limit number of rows read from each csv.')
    parser.add_argument(
        '--on',
        metavar='COLS',
        help=('Comma delimited list of column '
              'names or indices if --no-header'))
    parser.add_argument(
        '--no-header',
        action='store_true',
        help='If no header available.')
    parser.add_argument(
        '--take-last',
        action='store_true',
        help='Take the last duplicate value. Default is first.')
    parser.add_argument(
        '--stack',
        action='store_true',
        help=('keep all lines, do not deduplicate'))


def action(args):
    # for debugging:
    # pandas.set_option('display.max_columns', None)
    # pd.set_option('display.max_rows', None)

    dfs = []
    columns = None  # to preserve column order
    for csv in args.csv:
        df = utils.read_csv(csv,
                            dtype=str,
                            nrows=args.limit,
                            comment='#',
                            na_filter=False,
                            header=None if args.no_header else 0)
        columns = df.columns
        dfs.append(df)

    df = pandas.concat(dfs, ignore_index=True)

    if not args.stack:
        if args.on:
            on = args.on.split(',')

            if args.no_header:
                on = map(int, on)

            df = df.groupby(by=on, sort=False)
            df = df.tail(1) if args.take_last else df.head(1)
        else:
            df = df.drop_duplicates(take_last=args.take_last)

    df.to_csv(args.out, columns=columns, index=False)
