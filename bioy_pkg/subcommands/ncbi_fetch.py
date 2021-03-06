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
Fetch sequences from NCBI's nucleotide database using genbank sequence identifiers (gb)
Output is a multi-fasta of retrieved sequences and a corresponding sequence info (csv) file

Note: If indexed bases are backwards (e.g. seq_stop > seq_stop) then they will be un-reversed
"""

import logging
import sys
import csv

from Bio import Entrez
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import NucleotideAlphabet

from bioy_pkg.sequtils import FETCH_HEADERS
from bioy_pkg.utils import Opener

fieldnames = ['id','seq_start','seq_stop']

log = logging.getLogger(__name__)

def build_parser(parser):
    parser.add_argument('sseqids', nargs='?', type=Opener('r'),
            default = sys.stdin,
            help = 'csv input file, each line containing gb,seq_start,seq_stop')
    parser.add_argument('-o', '--outfasta',
            type = Opener('w'),
            default = sys.stdout,
            help = 'multi-fasta, one sequence for each provided identifier')
    parser.add_argument('-i', '--seqinfo',
            type = Opener('w'),
            help = "optionally output seqinfo for each sequence : {}".format(FETCH_HEADERS))
    parser.add_argument('-n', '--no-header',
            help = "suppress seqinfo header")
    parser.add_argument('-e', '--email', required=True,
            help = "users of NCBI Entrez API should provide email.  if usage is excessive, ncbi may block access to its API")

def parse_taxid(seq_record):
    taxid = ''
    features = seq_record['GBSeq_feature-table']
    for feature in features:
        for qual in feature['GBFeature_quals']:
            if 'taxon' in qual['GBQualifier_value']:
                taxid = qual['GBQualifier_value'].split(':')[-1]
                return taxid
    # In this case, no valid taxid was found
    return taxid

def retrieve_record(seq_id, seq_start, seq_stop):
    seq_handle = Entrez.efetch(db="nuccore", id=seq_id,
                               seq_start=seq_start,
                               seq_stop=seq_stop,
                               retmode="xml")

    try:
        seq_records = Entrez.read(seq_handle)
    except:
        log.info("unable to parse seqid '{}'".format(seq_id))
        raise


    seq_record = seq_records[0]


    # Extract TaxID from Genbank feature table
    taxid = parse_taxid(seq_record)
    description = seq_record['GBSeq_definition']
    sequence = seq_record['GBSeq_sequence'].upper()
    if seq_start and seq_stop:
        assert(len(sequence) <= abs(int(seq_stop) - int(seq_start))+1)

    seqids = ''.join(seq_record['GBSeq_other-seqids'])
    assert(len(seqids) >= 1)
    seqid = ''.join(seqids) # Joins genbank ids, which include '|'
    return SeqRecord(Seq(sequence, NucleotideAlphabet),
                         id=seqid,
                         description=description,
                         annotations={'taxid':taxid})

def action(args):

    Entrez.email = args.email

    sseqids = csv.DictReader(args.sseqids, fieldnames=fieldnames)

    if args.seqinfo:
        info = csv.writer(args.seqinfo, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        if not args.no_header:
            info.writerow(FETCH_HEADERS)

    # For each subject line in the input, fetch the sequence and output to fasta

    records = [retrieve_record(subject['id'], subject['seq_start'], subject['seq_stop'])
               for subject in sseqids]
    SeqIO.write(records, args.outfasta, 'fasta')
    if args.seqinfo:
        info.writerows([[seq.id, seq.annotations['taxid'], seq.description] for seq in records])
    args.outfasta.close()
