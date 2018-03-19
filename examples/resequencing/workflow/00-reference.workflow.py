# flake8: NOQA
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# 00-reference.workflow.py
#

import os
import sys

from gpipe.dsl import *


# ================================================================================
#
# ================================================================================

reference = import_relative_file('./libs/reference.py')
common = import_relative_file('./common.py')


# ================================================================================
#
# ================================================================================

options.validate({'reference': common.REFERENCE_SCHEMA})
reference.update_reference_options(options.reference)


# ================================================================================
#
# ================================================================================

def verify_par_masked(fasta, pars, non_pars):
    cpus(1)
    memory('4GB')

    parameter('python',     sys.executable)
    parameter('pars',       pars)
    parameter('non_pars',   non_pars)

    input('fasta',                      fasta)
    output('fasta_par_mask_verified',   f'{fasta}.par_mask_verified')

    script(r"""
        {{ python }} {{ workflow_directory }}/scripts/x-verify_par_masked.py\{% for p in pars %}
            --par {{ p.chrY }}\{% endfor %}{% for np in non_pars %}
            --non-par {{ np.chrY }}\{% endfor %}
            {{ fasta }}

        touch {{ fasta_par_mask_verified }}
    """)


def mask_pars(fasta_par2, fasta_par3, pars):
    cpus(1)
    memory('4GB')

    parameter('python',     sys.executable)
    parameter('pars',       pars)

    input('fasta_par2',     fasta_par2)
    output('fasta_par3',    fasta_par3)

    script(r"""
        {{ python }} {{ workflow_directory }}/scripts/x-mask_fasta.py\{% for p in pars %}
            --mask {{ p.chrY }}\{% endfor %}
            {{ fasta_par2 }}\
        > {{ fasta_par3 }}
    """)


def shift_chrMT(fasta_original, fasta_mt_shifted, shift_size):
    cpus(1)
    memory('4GB')

    parameter('python',     sys.executable)
    parameter('shift_size', shift_size)

    input('fasta_original',                 fasta_original)
    input('fasta_original_mt_interval_ist', f'{fasta_original}.chrMT.interval_list')
    output('fasta_mt_shifted',              fasta_mt_shifted)

    script(r"""
        # options.reference.contigs.chrMT might be null, thus, we have to manually resolve contig name
        chrMT=$(cat {{ fasta_original_mt_interval_ist }} | awk 'END { print $1 }')

        #
        {{ python }} {{ workflow_directory }}/scripts/x-shift_fasta.py\
            --shift $chrMT:{{ shift_size }}\
            {{ fasta_original }}\
        > {{ fasta_mt_shifted }}
    """)


def bwa_index(fasta):
    module(common.BWA_MODULE)

    cpus(1)
    memory('32GB')

    input('fasta',      fasta)
    output('fasta_amb', f'{fasta}.amb')
    output('fasta_ann', f'{fasta}.ann')
    output('fasta_bwt', f'{fasta}.bwt')
    output('fasta_pac', f'{fasta}.pac')
    output('fasta_sa',  f'{fasta}.sa')

    script(r"""
        bwa index {{ fasta }}
    """)


def samtools_faidx(fasta):
    module(common.SAMTOOLS_MODULE)

    cpus(1)
    memory('4GB')

    input('fasta',      fasta)
    output('fasta_fai', f'{fasta}.fai')

    script(r"""
        samtools faidx {{ fasta }}
    """)


def samtools_dict(fasta):
    module(common.SAMTOOLS_MODULE)

    cpus(1)
    memory('4GB')

    input('fasta',  fasta)
    output('dict',  os.path.splitext(fasta)[0] + '.dict')

    script(r"""
        samtools dict {{ fasta }} -o {{ dict }}
    """)


def generate_interval_lists(fasta):
    cpus(1)
    memory('4GB')

    parameter('python', sys.executable)

    input('dict',       os.path.splitext(fasta)[0] + '.dict')
    output('autosome',  f'{fasta}.autosome.interval_list')
    output('chrX',      f'{fasta}.chrX.interval_list')
    output('chrY',      f'{fasta}.chrY.interval_list')
    output('chrMT',     f'{fasta}.chrMT.interval_list')

    script(r"""
        python={{ python }}
        script={{ workflow_directory }}/scripts/x-generate_interval_list_from_dict.py
        dict={{ dict }}

        $python $script --autosome $dict > {{ autosome }}
        $python $script --chrX     $dict > {{ chrX }}
        $python $script --chrY     $dict > {{ chrY }}
        $python $script --chrMT    $dict > {{ chrMT }}
    """)


# ================================================================================
# Original
# ================================================================================

with task('s00-ORIG-verify_PARs_masked'):
    verify_par_masked(
        options.reference.fasta,
        [p for p in options.reference.chrXY.PARs if p.id != 'XTR'],
        [p for p in options.reference.chrXY.PARs if p.id == 'XTR'])

with task('s01-ORIG-bwa_index'):
    bwa_index(options.reference.fasta)

with task('s02-ORIG-samtools_faidx'):
    samtools_faidx(options.reference.fasta)

with task('s03-ORIG-samtools_dict'):
    samtools_dict(options.reference.fasta)

with task('s04-ORIG-interval_list'):
    generate_interval_lists(options.reference.fasta)


# ================================================================================
# PAR3
# ================================================================================

with task('s10-PAR3-mask_PARs'):
    mask_pars(
        options.reference.fasta_PAR2,
        options.reference.fasta_PAR3,
        options.reference.chrXY.PARs3)

with task('s11-PAR3-bwa_index'):
    bwa_index(options.reference.fasta_PAR3)

with task('s12-PAR3-samtools_faidx'):
    samtools_faidx(options.reference.fasta_PAR3)

with task('s13-PAR3-samtools_dict'):
    samtools_dict(options.reference.fasta_PAR3)

with task('s14-PAR3-interval_list'):
    generate_interval_lists(options.reference.fasta_PAR3)


# ================================================================================
# MT
# ================================================================================

with task('s20-MT-shift_chrMT'):
    shift_chrMT(
        options.reference.fasta,
        options.reference.fasta_mt_shifted,
        options.reference.chrMT.shift_size)

with task('s21-MT-bwa_index'):
    bwa_index(options.reference.fasta_mt_shifted)

with task('s22-MT-samtools_faidx'):
    samtools_faidx(options.reference.fasta_mt_shifted)

with task('s23-MT-samtools_dict'):
    samtools_dict(options.reference.fasta_mt_shifted)

with task('s24-MT-interval_list'):
    generate_interval_lists(options.reference.fasta_mt_shifted)
