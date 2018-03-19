#!/usr/bin/env python3
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# x-mask_fasta.py
#

import argparse
import collections
import sys

from gpipe.dsl import import_relative_file


fasta = import_relative_file('../libs/fasta.py')


def main():
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('fasta')
    parser.add_argument('--mask', dest='masks', action='append', default=[])
    args = parser.parse_args()

    #
    chromosome_regions_map = collections.defaultdict(list)
    for mask in args.masks:
        chromosome, start_and_end = mask.split(':')
        start, end = map(int, start_and_end.split('-'))
        chromosome_regions_map[chromosome].append((start, end))

    #
    with open(args.fasta) as fin:
        for header, sequence in fasta.parse_fasta(fin):
            #
            id = header.split()[0]
            if id in chromosome_regions_map:
                regions = chromosome_regions_map[id]
                header = '{} (masked: {})'.format(header, ', '.join(f'{s}-{e}'for s, e in regions))
                sequence = _mask_sequence(sequence, regions)

            #
            fasta.write_fasta(header, sequence, sys.stdout)


def _mask_sequence(sequence, regions):
    for start, end in regions:
        head = sequence[:start-1]       # NOQA: E226
        par = sequence[start-1:end-1]   # NOQA: E226
        tail = sequence[end-1:]         # NOQA: E226
        sequence = head + ('N' * len(par)) + tail

    return sequence


if __name__ == '__main__':
    main()
