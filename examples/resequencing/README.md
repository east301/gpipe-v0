# resequencing example

## prerequisites

  * [Environment Modules](http://modules.sourceforge.net/)
  * [Python 3.6 or later](https://www.python.org/)

  * [BCFTools](http://www.htslib.org/)
  * [FastQC](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/)
  * [Genome Analysis Toolkit 3.x](https://software.broadinstitute.org/gatk/)
  * [Picard](https://broadinstitute.github.io/picard/)
  * [Samtools](http://www.htslib.org/)


## how to run

    python3.6 -m venv gpipe-env
    source ./gpipe-env/bin/activate
    pip install gpipe

    ./step1-prepare.sh
    vi ./workflow/modules/[module file]

    ./step2-submit_reference.sh --dry-run
    ls -lah ./data/reference/hs37d5/logs/*.dry_run/

    ./step2-submit_reference.sh
    qstat
    # wait until all tasks are finished
    ls -lah ./data/reference/hs37d5

    ./step3-submit_sample.sh --dry-run --dry-run
    ls -lah ./data/sample/HG005/logs/*.dry_run/

    ./step3-submit_sample.sh
    qstat
    # wait until all tasks are finished
    ls -lah ./data/sample/HG005
