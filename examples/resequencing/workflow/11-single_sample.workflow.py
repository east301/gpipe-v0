# flake8: NOQA
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# 11-sigle_sample.workflow.py
#

from gpipe.dsl import *


# ================================================================================
#
# ================================================================================

common = import_relative_file('./common.py')
reference = import_relative_file('./libs/reference.py')


# ================================================================================
#
# ================================================================================

options.validate({
    'reference': common.REFERENCE_SCHEMA,
    'sample': {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'sex': {'type': ['integer', 'null']},
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
        },
        'required': ['id', 'sex', 'fastqs']
    }
})

reference.update_reference_options(options.reference)


# ================================================================================
#
# ================================================================================

def fastqc(fastq):
    module(common.FASTQC_MODULE)

    cpus(4)
    memory('4GB')

    input('fastq',  fastq)
    output('html',  fastq.replace('.fastq.gz', '') + '_fastqc.html')
    output('zip',   fastq.replace('.fastq.gz', '') + '_fastqc.zip')

    script(r"""
        fastqc -t {{ cpus }} --nogroup -o . {{ fastq }}
    """)


def bwa_mem(reference_fasta, fastq_id, fastq_r1, fastq_r2, bam):
    module(common.BWA_MODULE)
    module(common.SAMTOOLS_MODULE)

    cpus(12)
    memory('2GB')
    use_temporary_directory()

    parameter('fastq_id',       fastq_id)

    input('reference_fasta',    reference_fasta)
    input('fastq_r1',           fastq_r1)
    output('bam',               bam)

    if fastq_r2:
        input('fastq_r2', fastq_r2)

    script(r"""
        bwa mem\
            -t 10\
            -K 10000000\
            -R "@RG\tID:{{ fastq_id }}\tSM:{{ options.sample.id }}\tPL:illumina\tLB:LIB"\{% if not fastq_r2 %}
            -p\{% endif %}
            {{ reference_fasta }}\
            {{ fastq_r1 }}\{% if fastq_r2 %}
            {{ fastq_r2 }}\{% endif %}
        | samtools sort\
            --threads 2\
            -T $TMPDIR/{{ bam|basename }}\
            --output-fmt BAM\
            -l 1\
            -o {{ bam }}
    """)


def picard_mark_duplicates(source_bams, output_bam):
    module(common.JAVA_MODULE)
    module(common.PICARD_MODULE)

    cpus(2)
    memory('16GB')
    use_temporary_directory()

    input('source_bams',        source_bams)
    output('output_bam',        output_bam)
    output('output_bam_bai',    f'{output_bam}.bai')
    output('output_metrics',    f'{output_bam}.rmdup_metrics')

    script(r"""
        java -XX:+UseSerialGC -Xmx24G -jar $PICARD_JAR MarkDuplicates\{% for s in source_bams %}
            INPUT={{ s }}\{% endfor %}
            OUTPUT={{ output_bam }}\
            METRICS_FILE={{ output_metrics }}\
            TMP_DIR=$TMPDIR\
            COMPRESSION_LEVEL=9\
            CREATE_INDEX=true\
            ASSUME_SORTED=true\
            REMOVE_DUPLICATES=false\
            VALIDATION_STRINGENCY=LENIENT

        mv {{ output_bam|without_extension }}.bai {{ output_bam_bai }}
    """)


def samtools_bam_metrics(bam):
    module(common.SAMTOOLS_MODULE)

    cpus(4)
    memory('3GB')

    input('bam',        bam)
    output('flagstat',  f'{bam}.flagstat')
    output('idxstats',  f'{bam}.idxstats')

    script(r"""
        samtools flagstat --threads {{ cpus }} {{ bam }} > {{ flagstat }}
        samtools idxstats                      {{ bam }} > {{ idxstats }}
    """)


def picard_collect_multiple_metrics(reference_fasta, bam):
    module(common.JAVA_MODULE)
    module(common.PICARD_MODULE)

    cpus(2)
    memory('16GB')
    use_temporary_directory()

    input('reference_fasta',                        reference_fasta)
    input('bam',                                    bam)
    output('alignment_summary_metrics',             f'{bam}.alignment_summary_metrics')
    output('bait_bias_detail_metrics',              f'{bam}.bait_bias_detail_metrics')
    output('bait_bias_summary_metrics',             f'{bam}.bait_bias_summary_metrics')
    output('base_distribution_by_cycle_metrics',    f'{bam}.base_distribution_by_cycle_metrics')
    output('base_distribution_by_cycle_pdf',        f'{bam}.base_distribution_by_cycle.pdf')
    output('error_summary_metrics',                 f'{bam}.error_summary_metrics')
    output('gc_bias.detail_metrics',                f'{bam}.gc_bias.detail_metrics')
    output('gc_bias.pdf',                           f'{bam}.gc_bias.pdf')
    output('gc_bias.summary_metrics',               f'{bam}.gc_bias.summary_metrics')
    output('insert_size_histogram_pdf',             f'{bam}.insert_size_histogram.pdf')
    output('insert_size_metrics',                   f'{bam}.insert_size_metrics')
    output('pre_adapter_detail_metrics',            f'{bam}.pre_adapter_detail_metrics')
    output('pre_adapter_summary_metrics',           f'{bam}.pre_adapter_summary_metrics')
    output('quality_by_cycle_metrics',              f'{bam}.quality_by_cycle_metrics')
    output('quality_by_cycle_pdf',                  f'{bam}.quality_by_cycle.pdf')
    output('quality_distribution_metrics',          f'{bam}.quality_distribution_metrics')
    output('quality_distribution.pdf',              f'{bam}.quality_distribution.pdf')

    script(r"""
        java -XX:+UseSerialGC -Xmx24G -jar $PICARD_JAR CollectMultipleMetrics\
            INPUT={{ bam }}\
            OUTPUT={{ bam }}\
            REFERENCE_SEQUENCE={{ reference_fasta }}\
            PROGRAM=null\
            PROGRAM=CollectAlignmentSummaryMetrics\
            PROGRAM=CollectInsertSizeMetrics\
            PROGRAM=QualityScoreDistribution\
            PROGRAM=MeanQualityByCycle\
            PROGRAM=CollectBaseDistributionByCycle\
            PROGRAM=CollectGcBiasMetrics\
            PROGRAM=CollectSequencingArtifactMetrics\
            TMP_DIR=$TMPDIR
    """)


def picard_collect_wgs_metrics(reference_fasta, bam, type):
    module(common.JAVA_MODULE)
    module(common.PICARD_MODULE)

    cpus(2)
    memory('16GB')
    use_temporary_directory()

    input('reference_fasta',            reference_fasta)
    input('reference_fasta_interval',   f'{reference_fasta}.{type}.interval_list')
    input('bam',                        bam)
    output('wgs_metrics',               f'{bam}.wgs_metrics_{type}')

    script(r"""
        java -XX:+UseSerialGC -Xmx24G -jar $PICARD_JAR CollectWgsMetrics\
            INPUT={{ bam }}\
            OUTPUT={{ wgs_metrics }}\
            REFERENCE_SEQUENCE={{ reference_fasta }}\
            INTERVALS={{ reference_fasta_interval }}\
            TMP_DIR=$TMPDIR
    """)


def gatk3_haplotype_caller(reference_fasta, bam, gvcf, region, ploidy):
    module(common.BCFTOOLS_MODULE)
    module(common.GATK3_MODULE)
    module(common.JAVA_MODULE)

    cpus(8)
    memory('5GB')
    use_temporary_directory()

    parameter('region', region)
    parameter('ploidy', ploidy)

    input('reference_fasta',    reference_fasta)
    input('bam',                bam)
    output('gvcf',              gvcf)

    script(r"""
        java -XX:+UseSerialGC -Xmx24G -jar $GATK3_JAR\
            -T HaplotypeCaller\
            -nct {{ cpus }}\
            -R {{ reference_fasta }}\
            -I {{ bam }}\
            -o {{ gvcf }}\
            -L {{ region }}\
            -ploidy {{ ploidy }}\
            --emitRefConfidence GVCF\
            --filter_mismatching_base_and_quals
    """)


def bcftools_concat(source_vcfs, output_vcf):
    module(common.BCFTOOLS_MODULE)

    cpus(4)
    memory('2GB')

    input('source_vcfs',        source_vcfs)
    output('output_vcf',        output_vcf)
    output('output_vcf_tbi',    output_vcf + '.tbi')

    script(r"""
        bcftools concat\
            --threads {{ cpus }}\
            --no-version\
            --output-type z\
            --output {{ output_vcf }}\{% for s in source_vcfs %}
            {{ s }}{% if not loop.last %}\{% endif %}{% endfor %}

        bcftools index\
            --threads {{ cpus }}\
            --tbi\
            {{ output_vcf }}
    """)


def extract_reads_from_bam(bam, regions, fastq):
    module(common.JAVA_MODULE)
    module(common.PICARD_MODULE)
    module(common.SAMTOOLS_MODULE)

    cpus(4)
    memory('4GB')
    use_temporary_directory()

    parameter('regions',    regions)

    input('bam',            bam)
    output('fastq',         fastq)

    script(r"""
        # extract reads from BAM
        bam={{ bam }}
        bam0=$TMPDIR/{{ bam|basename }}.merged.bam
        bam1=$TMPDIR/{{ bam|basename }}.unmapped1.bam
        bam2=$TMPDIR/{{ bam|basename }}.unmapped2.bam
        bam3=$TMPDIR/{{ bam|basename }}.unmapped3.bam
        bam4=$TMPDIR/{{ bam|basename }}.mapped.bam

        samtools view --threads {{ cpus }} -b -u -f  4 -F 264 -o $bam1 $bam
        samtools view --threads {{ cpus }} -b -u -f  8 -F 260 -o $bam2 $bam
        samtools view --threads {{ cpus }} -b -u -f 12 -F 256 -o $bam3 $bam
        samtools view --threads {{ cpus }} -b -u       -F 268 -o $bam4 $bam {{ regions|join(' ') }}

        #
        samtools merge\
            --threads 2\
            -\
            $bam1 $bam2 $bam3 $bam4\
        | samtools sort\
            --threads 2\
            -n\
            -\
        | java -XX:+UseSerialGC -Xmx4G -jar $PICARD_JAR SamToFastq\
            INPUT=/dev/stdin\
            FASTQ={{ fastq }}\
            INTERLEAVE=true\
            INCLUDE_NON_PF_READS=true\
            RE_REVERSE=true\
            VALIDATION_STRINGENCY=SILENT
    """)


def get_chrXY_variant_call_regions_PAR2():
    x_name = options.reference.contigs.chrX.id
    y_name = options.reference.contigs.chrY.id
    sex = options.sample.sex

    par1_start, par1_end = get_chrX_PAR_region('PAR1')
    par2_start, par2_end = get_chrX_PAR_region('PAR2')

    #
    yield 'X_PAR1', f'{x_name}:{par1_start}-{par1_end}',   2
    yield 'X_CORE', f'{x_name}:{par1_end+1}-{par2_end-1}', sex
    yield 'X_PAR2', f'{x_name}:{par2_start}-{par2_end}',   2

    if sex == 1:
        yield 'Y_CORE', f'{y_name}', 1


def get_chrXY_variant_call_regions_PAR3():
    x_name = options.reference.contigs.chrX.id
    y_name = options.reference.contigs.chrY.id
    sex = options.sample.sex

    par1_start, par1_end = get_chrX_PAR_region('PAR1')
    xtr_start, xtr_end = get_chrX_PAR_region('XTR')
    par2_start, par2_end = get_chrX_PAR_region('PAR2')

    #
    yield 'X_PAR1',  f'{x_name}:{par1_start}-{par1_end}',    2
    yield 'X_CORE1', f'{x_name}:{par1_end+1}-{xtr_end-1}',   sex
    yield 'X_XTR',   f'{x_name}:{xtr_start}-{xtr_end}',      2
    yield 'X_CORE2', f'{x_name}:{xtr_end+1}-{par2_start-1}', sex
    yield 'X_PAR2',  f'{x_name}:{par2_start}-{par2_end}',    2

    if sex == 1:
        yield 'Y_CORE',  f'{y_name}', 1


def get_chrX_PAR_region(id):
    par = [p for p in options.reference.PARs if p.id == id][0]
    return list(map(int, par.chrX.split(':')[0].split('-')))


# ================================================================================
# autosome
# ================================================================================

for entry in options.sample.fastqs:
    with task('s00-BASE-fastqc'):
       fastqc(entry.r1)

    with task('s00-BASE-fastqc'):
       fastqc(entry.r2)

    with task('s01-BASE-bwa_mem_align'):
        bwa_mem(
            options.reference.fasta_PAR2,
            entry.id,
            entry.r1,
            entry.r2,
            f'{entry.id}.bwamem.bam')


with task('s02-BASE-rmdup'):
    picard_mark_duplicates(
        resolve_outputs('s01-BASE-bwa_mem_align', 'bam'),
        '{{ options.sample.id }}.bwamem.bam')


with task('s03-BASE-samtools_bam_metrics'):
    samtools_bam_metrics('{{ options.sample.id }}.bwamem.bam')


with task('s04-BASE-picard_bam_metrics'):
    picard_collect_multiple_metrics(
        options.reference.fasta_PAR2,
        '{{ options.sample.id }}.bwamem.bam')


for type in ['autosome', 'chrX', 'chrY', 'chrMT']:
    with task('s04-BASE-picard_bam_metrics'):
        picard_collect_wgs_metrics(
            options.reference.fasta_PAR2,
            '{{ options.sample.id }}.bwamem.bam',
            type)


for contig_key, contig_entry in options.reference.contig_dict.items():
    if contig_entry.type != 'AUTOSOME':
        continue

    with task('s05-BASE-gvcf_autosome'):
        gatk3_haplotype_caller(
            options.reference.fasta,
            '{{ options.sample.id }}.bwamem.bam',
            temporary('{{ options.sample.id }}.bwamem.hc3.autosome_%s.g.vcf.gz' % contig_key),
            contig_entry.id,
            2)


with task('s06-BASE-gvcf_autosome_concat'):
    bcftools_concat(
        resolve_outputs('s05-BASE-gvcf_autosome', 'gvcf'),
        '{{ options.sample.id }}.bwamem.hc3.autosome.g.vcf.gz')


# ================================================================================
# PAR2
# ================================================================================

if options.sample.sex is not None:
    for name, region, ploidy in get_chrXY_variant_call_regions_PAR2():
        with task('s11-PAR2-gvcf_chrXY'):
            gatk3_haplotype_caller(
                options.reference.fasta,
                '{{ options.sample.id }}.bwamem.bam',
                '{{ options.sample.id }}.bwamem.hc3.chrXY_PAR2_%s.g.vcf.gz' % name,
                region,
                ploidy)

    with task('s12-PAR2-gvcf_chrXY_concat'):
        bcftools_concat(
            resolve_outputs('s11-PAR2-gvcf_chrXY', 'gvcf'),
            '{{ options.sample.id }}.bwamem.hc3.chrXY_PAR2.g.vcf.gz')


# ================================================================================
# PAR3
# ================================================================================

with task('s20-PAR3-extract_reads'):
    extract_reads_from_bam(
        '{{ options.sample.id }}.bwamem.bam',
        [options.reference.contigs.chrX.id, options.reference.contigs.chrY.id],
        '{{ options.sample.id }}.bwamem.bam.chrXY.interleaved.fastq.gz')


with task('s21-PAR3-bwa_mem'):
    bwa_mem(
        options.reference.fasta_PAR3,
        f'{options.sample.id}_chrXY',
        '{{ options.sample.id }}.bwamem.bam.chrXY.interleaved.fastq.gz',
        None,
        temporary('{{ options.sample.id }}.bwamem.chrXY_PAR3_dup.bam'))


with task('s22-PAR3-rmdup'):
    picard_mark_duplicates(
        ['{{ options.sample.id }}.bwamem.chrXY_PAR3_dup.bam'],
        '{{ options.sample.id }}.bwamem.chrXY_PAR3.bam')


with task('s23-PAR3-samtools_bam_metrics'):
    samtools_bam_metrics('{{ options.sample.id }}.bwamem.chrXY_PAR3.bam')


with task('s24-PAR3-picard_bam_metrics'):
    picard_collect_multiple_metrics(
        options.reference.fasta_PAR3,
        '{{ options.sample.id }}.bwamem.chrXY_PAR3.bam')


for type in ['chrX', 'chrY']:
    with task('s24-PAR3-picard_bam_metrics'):
        picard_collect_wgs_metrics(
            options.reference.fasta_PAR3,
            '{{ options.sample.id }}.bwamem.chrXY_PAR3.bam', type)


if options.sample.sex is not None:
    for name, region, ploidy in get_chrXY_variant_call_regions_PAR3():
        with task('s25-PAR3-gvcf_chrXY'):
            gatk3_haplotype_caller(
                options.reference.fasta_PAR3,
                '{{ options.sample.id }}.bwamem.bam',
                temporary('{{ options.sample.id }}.bwamem.hc3.chrXY_PAR3_%s.g.vcf.gz' % ploidy),
                region,
                ploidy)

    with task('s26-PAR3-gvcf_chrXY_concat'):
        bcftools_concat(
            resolve_outputs('s25-PAR3-gvcf_chrXY', 'gvcf'),
            '{{ options.sample.id }}.bwamem.hc3.chrXY_PAR3.g.vcf.gz')


# ================================================================================
# chrMT
# ================================================================================

with task('s30-MT-extract_reads'):
    extract_reads_from_bam(
        '{{ options.sample.id }}.bwamem.bam',
        [options.reference.contigs.chrMT.id],
        '{{ options.sample.id }}.bwamem.bam.chrMT.interleaved.fastq.gz')


for reference_fasta in [options.reference.fasta, options.reference.fasta_mt_shifted]:
    type = 'chrMT_original' if reference_fasta == options.reference.fasta else 'chrMT_shifted'
    aligned_bam = '{{ options.sample.id }}.bwamem.%s_dup.bam' % type
    deduped_bam = '{{ options.sample.id }}.bwamem.%s.bam' % type
    gvcf = '{{ options.sample.id }}.bwamem.hc3.%s.g.vcf.gz' % type

    with task('s32-MT-bwa_mem'):
        bwa_mem(
            reference_fasta,
            f'{options.sample.id}_chrMT',
            '{{ options.sample.id }}.bwamem.bam.chrMT.interleaved.fastq.gz',
            None,
            temporary(aligned_bam))


    with task('s32-MT-rmdup'):
        picard_mark_duplicates([aligned_bam], deduped_bam)


    with task('s33-MT-samtools_bam_metrics'):
        samtools_bam_metrics(deduped_bam)


    with task('s34-MT-picard_bam_metrics'):
        picard_collect_multiple_metrics(reference_fasta, deduped_bam)


    with task('s34-MT-picard_bam_metrics'):
        picard_collect_wgs_metrics(reference_fasta, deduped_bam, 'chrMT')


    with task('s35-MT-variant_call'):
        gatk3_haplotype_caller(
            reference_fasta, deduped_bam, gvcf, options.reference.contigs.chrMT.id, 1)
