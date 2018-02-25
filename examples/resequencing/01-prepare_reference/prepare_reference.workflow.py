#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# prepare_reference.workflow.py
#

from gpipe.dsl import *     # NOQA


# ================================================================================
# options
# ================================================================================

options.validate({
    'prepare_reference': {
        'type': 'object',
        'properties': {
            'fasta': {'type': 'string'}
        },
        'required': ['fasta']
    }
})


# ================================================================================
# tasks - BWA
# ================================================================================

with task('bwa_index'):
    # module('bwa/0.7.15')

    input('fasta',      '{{ options.prepare_reference.fasta }}')
    output('fasta_amb', '{{ options.prepare_reference.fasta }}.amb')
    output('fasta_ann', '{{ options.prepare_reference.fasta }}.ann')
    output('fasta_bwt', '{{ options.prepare_reference.fasta }}.bwt')
    output('fasta_pac', '{{ options.prepare_reference.fasta }}.pac')
    output('fasta_sa',  '{{ options.prepare_reference.fasta }}.sa')

    cpus(1)
    memory('16GB')

    script("""
        bwa index {{ fasta }}
    """)


# ================================================================================
# tasks - Samtools
# ================================================================================

with task('samtools_faidx'):
    # module('samtools/1.7')

    input('fasta',      '{{ options.prepare_reference.fasta }}')
    output('fasta_fai', '{{ options.prepare_reference.fasta }}.fai')

    cpus(1)
    memory('2GB')

    script("""
        samtools faidx {{ fasta }}
    """)


with task('samtools_faidx'):
    # module('samtools/1.7')

    input('fasta',  '{{ options.prepare_reference.fasta }}')
    output('dict',  '{{ options.prepare_reference.fasta|without_extension }}.dict')

    cpus(1)
    memory('2GB')

    script("""
        samtools dict {{ fasta }} --output {{ dict }}
    """)
