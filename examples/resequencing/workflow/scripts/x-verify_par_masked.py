#!/usr/bin/env python3
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# x-verify_par_masked.py
#

import argparse
import collections

from gpipe.dsl import import_relative_file


fasta = import_relative_file('../libs/fasta.py')


def main():
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('fasta')
    parser.add_argument('--par', dest='pars', action='append', default=[])
    parser.add_argument('--non-par', dest='non_pars', action='append', default=[])
    args = parser.parse_args()

    if not args.pars:
        return

    #
    chromosome_par_regions_map = _create_chromosome_region_map(args.pars)
    chromosome_non_par_regions_map = _create_chromosome_region_map(args.non_pars)

    #
    with open(args.fasta) as fin:
        for header, sequence in fasta.parse_fasta(fin):
            #
            id = header.split()[0]

            if id in chromosome_par_regions_map:
                for start, end, par in _extract_regions(sequence, chromosome_par_regions_map[id]):
                    if set(par.upper()) != set(['N']):
                        raise Exception(f'PAR not masked: {id}:{start}-{end}')

            elif id in chromosome_non_par_regions_map:
                for start, end, non_par in _extract_regions(sequence, chromosome_non_par_regions_map[id]):
                    if len(set(par.upper()) - set(['N'])) > 0:
                        raise Exception(f'non-PAR masked: {id}:{start}-{end}')


def _create_chromosome_region_map(regions):
    chromosome_regions_map = collections.defaultdict(list)
    for mask in regions:
        chromosome, start_and_end = mask.split(':')
        start, end = map(int, start_and_end.split('-'))
        chromosome_regions_map[chromosome].append((start, end))

    return chromosome_regions_map


def _extract_regions(sequence, regions):
    for start, end in regions:
        yield start, end, sequence[start-1:end-1]   # NOQA: E226


if __name__ == '__main__':
    main()
