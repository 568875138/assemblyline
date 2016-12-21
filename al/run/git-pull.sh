#!/bin/sh

. /etc/default/al

branches() {
    {
        python - $@ 2>&1 | grep '^BRANCH:' | sed -e 's/BRANCH: //g' | sort
    } <<EOF
import os, sys
from assemblyline.al.common import forge
datastore = forge.get_datastore()
bootstrap = datastore.get_blob('seed')
repos = bootstrap.get('system', {}).get('repositories', {})
for k, v in repos.iteritems():
    print "BRANCH: " + k + "\t" + os.environ.get('AL_BRANCH', v.get('branch', 'master'))
EOF
}

branches |
while read Repo Branch; do
    echo "Updating ${Repo} (${Branch}):"
    [ "${Branch}" != unknown ] &&
    Path=${PYTHONPATH}/${Repo}
    (cd $Path &&
     git checkout --force ${Branch} &&
     git fetch --all &&
     git reset --hard origin/${Branch}) 2>&1 |
    grep -Ev '^(Already on|Your branch is up-to-date with) ' |
    grep -Ev '^Fetching origin$' |
    sed -e "s|HEAD is||g" -e 's|^|\t|g'
    echo
done

