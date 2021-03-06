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

"""Provide some fasta or fastq plots for length distribution and quality scores
"""

import logging

import matplotlib as plt
import pandas as pd

from bioy_pkg.utils import Opener
from bioy_pkg.sequtils import fastalite
log = logging.getLogger(__name__)


def build_parser(parser):
    # required inputs
    parser.add_argument(
        'intype',
        choices=['fasta', 'csv'],
        help='plot either and fasta or csv file')
    parser.add_argument(
        'infile',
        type=Opener(),
        help='CSV tabular blast file of query and subject hits.')

    # common outputs
    parser.add_argument(
        '-o', '--out',
        metavar='FILE',
        default='plot.pdf',
        help="Classification results.")
    parser.add_argument(
        '--column',
        help=('if csv is specified select a column to plot'))
    parser.add_argument(
        '--xaxis',
        help='plot x axis')
    parser.add_argument(
        '--title',
        help=('density plot title'))

    parser.add_argument(
        '--limit', type=int, help='limit number of rows read')


def action(args):
    # for debugging:
    # pd.set_option('display.max_columns', None)
    # pd.set_option('display.max_rows', None)

    if args.intype == 'fasta':
        fa = fastalite(args.infile, limit=args.limit)
        df = pd.Series(data={f.id: f.seq for f in fa}, name='seq')
        df = df.reset_index()
        df = df.set_index('index')
        df.index.name = 'id'
        df['length'] = df['seq'].apply(len)
        column = 'length'
    else:  # elif args.intpe == 'csv':
        df = pd.read_csv(args.infile)
        column = args.column

    xticks = args.xaxis.split(',') if args.xaxis else None

    # do not display plots
    plt.use('Agg')

    # format blast data and add additional available information
    pl = df[column].plot(kind='kde',
                         title=args.title,
                         xticks=xticks)

    log.info('printing to {}'.format(args.out))

    pl.get_figure().savefig(args.out)
