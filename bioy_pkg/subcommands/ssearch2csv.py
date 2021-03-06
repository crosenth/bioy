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

"""
Parse ssearch36 -m10 output and print specified contents
"""

import logging
import sys
import pprint
import csv

from itertools import islice, chain, groupby, imap
from operator import itemgetter

from bioy_pkg.sequtils import homodecodealignment, parse_ssearch36, from_ascii, CAPUI
from bioy_pkg.utils import Opener, Csv2Dict, parse_extras

log = logging.getLogger(__name__)


def is_similar(a, b):
    try:
        return True if a == b else bool(CAPUI[a] & CAPUI[b])
    except KeyError:
        return False


def add_diff(align):
    """Extract the aligned regions of q_seq and t_seq. Non-identical
    characters are in lower case.

    """

    qstart, qstop, tstart, tstop = [int(align[k]) for k in [
        'q_al_start', 'q_al_stop', 't_al_start', 't_al_stop']]

    qstr = align['q_seq'].strip('-')[qstart - 1:qstop]
    tstr = align['t_seq'].strip('-')[tstart - 1:tstop]
    qchars, tchars = zip(*[('.', t) if is_similar(q, t) else (q.lower(), t.lower())
                           for q, t in zip(qstr, tstr)])

    return dict(align, q_diff=''.join(qchars), t_diff=''.join(tchars))


def build_parser(parser):
    parser.add_argument('alignments',
        default = sys.stdin,
        type = Opener('r'),
        nargs = '?',
        help = 'ssearch -m 10 formatted file')
    parser.add_argument('-o', '--out',
        default = sys.stdout,
        type = Opener('w'),
        help = '(default csv)-formatted output')
    parser.add_argument('-p', '--print-one',
        default = False, action = 'store_true',
        help = 'pretty print first alignment and exit')
    parser.add_argument('-f', '--fieldnames',
        type = lambda f: f.split(','),
        help = 'comma-delimited list of field names to include in output')
    parser.add_argument('--limit',
        type = int,
        metavar = 'N',
        help = 'Print no more than N alignments')
    parser.add_argument('--no-header',
        dest='header',
        action = 'store_false')
    parser.add_argument('-r', '--rlefile',
        type = Csv2Dict(index = 'name', value = 'rle',
            fieldnames = ['name', 'rle']),
        nargs = '+',
        help = 'CSV file containing run-length encoding')
    parser.add_argument('--min-zscore',
        default = None,
        type = float,
        metavar = 'X',
        help = 'Exclude alignments with z-score < X')
    parser.add_argument('-a', '--top-alignment',
        default = False, action = 'store_true',
        help = """By default, return all alignments;
                  provide this option to include
                  only the top entry per query.""")
    parser.add_argument('-e', '--extra-fields',
            help="extra fields for csv file in form 'name1:val1,name2:val2'")
    parser.add_argument('-d', '--with-diff', action='store_true', default=False,
            help="""add fields 'q_diff' and 't_diff' containing
            aligned substrings with mismatches in lowercase""")

def action(args):
    extras = parse_extras(args.extra_fields) if args.extra_fields else {}

    aligns = islice(parse_ssearch36(args.alignments, False), args.limit)

    if args.min_zscore:
        aligns = (a for a in aligns if float(a['sw_zscore']) >= args.min_zscore)
    aligns = groupby(aligns, key = itemgetter('q_name'))

    if args.top_alignment:
        aligns = (next(a) for _, a in aligns)
    else:
        aligns = (a for _, i in aligns for a in i)  # flatten groupby iters

    if args.rlefile:
        decoding = {k:v for d in args.rlefile for k,v in d.items()}
        def decode(aligns):
            aligns['t_seq'], aligns['q_seq'] = homodecodealignment(
                    aligns['t_seq'], from_ascii(decoding[aligns['t_name']]),
                    aligns['q_seq'], from_ascii(decoding[aligns['q_name']]))
            return aligns
        aligns = imap(decode, aligns)

    if args.print_one:
        pprint.pprint(aligns.next())
        sys.exit()

    if args.with_diff:
        aligns = imap(add_diff, aligns)

    if args.fieldnames:
        fieldnames = args.fieldnames
    else:
        # peek at first row fieldnames
        top = next(aligns, {})
        fieldnames = top.keys()
        aligns = chain([top], aligns)

    if extras:
        fieldnames += extras.keys()
        aligns = (dict(d, **extras) for d in aligns)

    writer = csv.DictWriter(args.out,
            extrasaction = 'ignore',
            fieldnames = fieldnames)

    if args.header:
        writer.writeheader()

    for a in aligns:
        writer.writerow(a)
