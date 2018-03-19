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
cd $(dirname $0)/data/reference/hs37d5

gpipe run hs37d5.gpipe.yml "$@"
