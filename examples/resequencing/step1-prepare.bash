#!/bin/bash
#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# setep1-prepare.sh
#

set -eux
cd $(dirname $0)

# copies ./workflow/modulefiles.template
if [ ! -d ./workflow/modulefiles ]; then
    cp -pr ./workflow/modulefiles.template ./workflow/modulefiles
fi

# downloads references and FASTQs
cat download_urls.txt | grep -v '#' | awk 'NF' | while read line; do
    url=$(echo "$line" | awk '{ print $2 }')
    destination=$(echo "$line" | awk '{ print $1 }')

    if [ ! -f $destination ]; then
        curl -o $destination $url
    fi
done

# decompress hs37d5.fa.gz
if [ ! -f ./data/reference/hs37d5/hs37d5.fa ]; then
    gzip -dc ./data/reference/hs37d5/hs37d5.fa.gz > ./data/reference/hs37d5/hs37d5.fa
fi
