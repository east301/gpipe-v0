#!/bin/bash
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# run.sh
#

cd $(dirname $0)

# ================================================================================
# downloads reference sequence
# ================================================================================

if [ ! -e chromFa.tar.gz ]; then
    curl -LO http://hgdownload.soe.ucsc.edu/goldenPath/sacCer3/bigZips/chromFa.tar.gz
fi
if [ ! -e saccer3.fa ]; then
    tar zxf chromFa.tar.gz -O > saccer3.fa
fi

# ================================================================================
# runs gpipe
# ================================================================================

gpipe run ../prepare_reference.workflow.py ./prepare_reference.saccer3.yml
