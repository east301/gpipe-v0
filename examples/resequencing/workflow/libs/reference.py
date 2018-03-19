#
# reference.py
#

import argparse
import collections
import os

from gpipe.utils.pyobject import convert_dict_to_ns


def update_reference_options(reference):
    #
    fasta_path = reference.fasta
    fasta_directory = os.path.dirname(fasta_path)
    fasta_name = os.path.splitext(os.path.basename(fasta_path))[0]
    fasta_extension = os.path.splitext(fasta_path)[1]

    #
    reference.fasta_PAR2 = reference.fasta
    reference.fasta_PAR3 = os.path.join(fasta_directory, f'{fasta_name}_PAR3{fasta_extension}')
    reference.fasta_mt_shifted = os.path.join(fasta_directory, f'{fasta_name}_MT_shifted{fasta_extension}')

    #
    reference.chrXY.PARs2 = [r for r in reference.chrXY.PARs if r.id != 'XTR']
    reference.chrXY.PARs3 = reference.chrXY.PARs

    #
    contig_dict = collections.OrderedDict()
    if os.path.exists(f'{fasta_path}.fai'):
        with open(f'{fasta_path}.fai') as fin:
            for line in fin:
                #
                contig_id, contig_length = line.split()[:2]

                contig_id_wo_prefix = contig_id.replace('chr', '')
                contig_length = int(contig_length)

                #
                if contig_id_wo_prefix.isdigit():
                    contig_key = f'chr{contig_id_wo_prefix}'
                    contig_type = 'AUTOSOME'
                elif contig_id_wo_prefix in ('X', 'Y'):
                    contig_key = f'chr{contig_id_wo_prefix}'
                    contig_type = 'chrXY'
                elif contig_id_wo_prefix in ('M', 'MT'):
                    contig_key = 'chrMT'
                    contig_type = 'chrMT'
                else:
                    # TODO: handle unlocalized/unplaced contigs
                    continue

                #
                contig_dict[contig_key] = argparse.Namespace(
                    id=contig_id, type=contig_type, length=contig_length)

    #
    reference.contigs = convert_dict_to_ns(contig_dict)
    reference.contig_dict = contig_dict
