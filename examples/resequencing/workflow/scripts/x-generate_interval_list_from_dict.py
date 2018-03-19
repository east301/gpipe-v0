#!/usr/bin/env python3
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# x-generate_interval_list_from_dict.py
#

import argparse


def main():
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('dict')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--autosome', action='store_true')
    group.add_argument('--chrX', action='store_true')
    group.add_argument('--chrY', action='store_true')
    group.add_argument('--chrMT', action='store_true')
    args = parser.parse_args()

    #
    chromosomes = []
    with open(args.dict) as fin:
        for line in fin:
            #
            line = line.strip()

            if line.startswith('@SQ'):
                cols = line.split('\t')
                sn = [c[3:] for c in cols if c.startswith('SN:')][0]
                ln = int([c[3:] for c in cols if c.startswith('LN:')][0])
                chromosomes.append((sn, ln))

            #
            print(line)

    #
    if args.autosome:
        do_check = lambda t: t.replace('chr', '').isdigit()
    elif args.chrX:
        do_check = lambda t: t.replace('chr', '') == 'X'
    elif args.chrY:
        do_check = lambda t: t.replace('chr', '') == 'Y'
    elif args.chrMT:
        do_check = lambda t: t.replace('chr', '') in ('M', 'MT')
    else:
        raise Exception

    for chromosome, length in chromosomes:
        if do_check(chromosome):
            print(f'{chromosome}\t1\t{length}\t+\t{chromosome}')


if __name__ == '__main__':
    main()
