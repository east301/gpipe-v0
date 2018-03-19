#!/usr/bin/env python3
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# x-shift_fasta.py
#

import argparse
import sys

from gpipe.dsl import import_relative_file


fasta = import_relative_file('../libs/fasta.py')


def main():
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('fasta')
    parser.add_argument('--shift', dest='shifts', action='append', default=[])
    args = parser.parse_args()

    #
    chromosome_shift_size_map = {}
    for shift in args.shifts:
        chromosome, shift_size = shift.split(':')
        chromosome_shift_size_map[chromosome] = int(shift_size)

    #
    with open(args.fasta) as fin:
        for header, sequence in fasta.parse_fasta(fin):
            #
            id = header.split()[0]
            if id in chromosome_shift_size_map:
                shift_size = chromosome_shift_size_map[id]
                header = f'{header} (shifted: {shift_size})'
                sequence = sequence[shift_size:] + sequence[:shift_size]

            #
            fasta.write_fasta(header, sequence, sys.stdout)


if __name__ == '__main__':
    main()
