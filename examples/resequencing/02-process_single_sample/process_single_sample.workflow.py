#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# process_single_sample.workflow.py
#

from gpipe.dsl import *     # NOQA


# ================================================================================
# option
# ================================================================================

options.validate({
    'process_single_sample': {
        'type': 'object',
        'properties': {
            'reference': {
                'type': 'object',
                'properties': {
                    'fasta': {'type': 'string'}
                },
                'required': ['fasata']
            },
            'sample': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'fastqs': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'r1': {'type': 'string'},
                                'r2': {'type': 'string'}
                            },
                            'required': ['id', 'r1', 'r2']
                        }
                    }
                }
            }
        },
        'required': ['reference', 'sample']
    }
})

# ================================================================================
# step1: alignment
# ================================================================================

for entry in options.process_single_sample.sample.fastqs:
    with task('bwa_mem'):
        # module('bwa/0.7.15')
        # module('samtools/1.7')

        input('reference_fasata',   '{{ options.process_single_sample.reference.fasta }}')
        input('fastq_r1',           entry.r1)
        input('fastq_r2',           entry.r2)
        output('bam',               f'{entry.id}.bwamem.bam')

        cpus(8)
        memory('2GB')
        use_temporary_directory()

        script("""
            bwa mem\
                -t {{ cpus - 2 }}\
                {{ reference_fasta }}\
                {{ fastq_r1 }}\
                {{ fastq_r2 }}\
            | samtools sort\
                --threads 2\
                -T $TMPDIR/{{ id }}\
                -l 1\
                --output-fmt BAM\
                -o {{ bam }}
        """)

with task('rmdup'):
    # module('java/1.8.0_162')
    # module('picard/2.10.6')

    input('reference_fasta',    '{{ options.process_single_sample.reference.fasta }}')
    input('source_bams',        resolve_outputs('bwa_mem', 'bam'))
    output('output_bam',        '{{ options.process_single_sample.sample.id }}.bwamem.bam')
    output('output_bam_bai',    '{{ options.process_single_sample.sample.id }}.bwamem.bam.bai')
    output('output_metrics',    '{{ options.process_single_sample.sample.id }}.bwamem.bam.rmdup_metrics')

    cpus(2)
    memory('16GB')
    use_temporary_directory()

    script(r"""
        java -Xmx24G -XX:+UseSerialGC -jar $PICARD_JAR MarkDuplicates\
            REFERENCE_SEQUENCE={{ reference_fasta }}\{% for s in source_bams %}
            INPUT={{ s }}\{% endfor %}
            OUTPUT={{ output_bam }}\
            METRICS_FILE={{ output_metrics }}\
            REMOVE_DUPLICATES=true\
            ASSUME_SORTED=true\
            COMPRESSION_LEVEL=9\
            CREATE_INDEX=true\
            TMP_DIR=$TMPDIR

        mv {{ output_bam|without_extension }}.bai {{ output_bam_bai }}
    """)


# ================================================================================
# step2: (single sample) variant call
# ================================================================================

with task('gvcf'):
    # module('java/1.8.0_162')
    # module('gatk/3.8')

    input('reference_fasta',    '{{ options.process_single_sample.reference.fasta }}')
    input('bam',                '{{ options.process_single_sample.sample.id }}.bwamem.bam')
    output('gvcf',              '{{ options.process_single_sample.sample.id }}.bwamem.hc3.g.vcf.gz')
    output('gvcf_tbi',          '{{ options.process_single_sample.sample.id }}.bwamem.hc3.g.vcf.gz.tbi')

    cpus(8)
    memory('6GB')

    script(r"""
        java -Xmx32G -XX:+UseSerialGC -jar $GATK_JAR\
            -T HaplotypeCaller\
            -nct {{ cpus }}\
            -R {{ reference_fasta }}\
            -I {{ bam }}\
            -o {{ gvcf }}\
            --emitRefConfidence GVCF
    """)
