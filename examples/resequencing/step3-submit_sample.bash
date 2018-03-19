#!/bin/bash
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# setep2-submit_reference.sh
#

set -eux
cd $(dirname $0)

cd data/sample/HG005
gpipe run HG005.gpipe.yml "$@"
