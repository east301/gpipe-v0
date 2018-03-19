# flake8: NOQA
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# common.py
#

# ================================================================================
# module
# ================================================================================

BCFTOOLS_MODULE     = 'bcftools-1.7'
BWA_MODULE          = 'bwa-0.7.12'
FASTQC_MODULE       = 'fastqc-0.11.2'
GATK3_MODULE        = 'gatk-3.8-0'
JAVA_MODULE         = 'java-1.8.0_162'
PICARD_MODULE       = 'picard-2.10.6'
SAMTOOLS_MODULE     = 'samtools-1.7'


# ================================================================================
# schema
# ================================================================================

REFERENCE_SCHEMA = {
    'type': 'object',
    'properties': {
        'fasta': {'type': 'string'},
        'has_chr_prefix': {'type': 'boolean'},
        'chrXY': {
            'type': 'object',
            'properties': {
                'PARs': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'chrX': {'type': 'string'},
                            'chrY': {'type': 'string'}
                        },
                        'required': ['id', 'chrX', 'chrY']
                    }
                }
            }
        },
        'chrMT': {
            'type': 'object',
            'properties': {
                'shift_size': {'type': 'integer'}
            },
            'required': ['shift_size']
        }
    },
    'required': ['fasta', 'has_chr_prefix', 'chrXY', 'chrMT']
}
