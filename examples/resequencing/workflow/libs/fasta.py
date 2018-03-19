#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# fasta.py
#


def parse_fasta(fin):
    #
    header = None
    sequence_fragments = None

    #
    for line in fin:
        #
        line = line.strip()
        if not line:
            continue

        #
        if line.startswith('>'):
            if header:
                yield header, ''.join(sequence_fragments)

            header = line[1:]
            sequence_fragments = []

        else:
            sequence_fragments.append(line)

    #
    if header:
        yield header, ''.join(sequence_fragments)


def write_fasta(header, sequence, fout, width=80):
    #
    if not header.startswith('>'):
        header = f'>{header}'

    #
    print(header, file=fout)
    print('\n'.join(sequence[i:i+width] for i in range(0, len(sequence), width)), file=fout)    # NOQA: E226
    print(file=fout)
