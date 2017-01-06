#!/bin/sh

. /etc/default/al

branch() {
    {
        python - $@ 2>&1 | grep '^BRANCH:' | sed -e 's/BRANCH: //g' | sort
    } <<EOF
import os, sys
from assemblyline.al.common import forge
datastore = forge.get_datastore()
bootstrap = datastore.get_blob('seed')
repo = bootstrap.get('system', {}).get('internal_repository', {})
print "BRANCH: " + os.environ.get('AL_BRANCH', repo.get('branch', 'master'))
EOF
}

git_update() {
    repo_path=$1
    repo=$2
    branch=$3
    if [ -d ${repo_path} ]; then
        echo "Updating ${repo} (${branch}):"
        (cd ${repo_path} &&
         git checkout --force ${branch} &&
         git fetch --all &&
         git reset --hard origin/${branch}) 2>&1 |
        grep -Ev '^(Already on|Your branch is up-to-date with) ' |
        grep -Ev '^Fetching origin$' |
        sed -e "s|HEAD is||g" -e 's|^|\t|g'
        echo
    fi
}

branch=`branch`
for repo in 'assemblyline' 'al_ui' 'al_private';
do
    repo_path=${PYTHONPATH}/${repo}
    git_update ${repo_path} ${repo} $branch
done

for svc in ${PYTHONPATH}/al_services/*;
do
    repo=`echo $svc | sed -e "s|${PYTHONPATH}/al_services/||g"`
    git_update $svc $repo $branch
done
