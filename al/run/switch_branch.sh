#!/bin/sh

[ $# -lt 1 ] && echo "usage: al_switch_branch <branch>" && exit 1

. /etc/default/al

switch_branch() {
    repo_path=$1
    repo=$2
    if [ -d ${repo_path} ]; then
        echo "Switching ${repo} to branch: $1:"
        (cd ${repo_path} &&
         git fetch --all &&
         git reset --hard origin/${1}) 2>&1 |
        grep -Ev '^(Already on|Your branch is up-to-date with) ' |
        grep -Ev '^Fetching origin$' |
        sed -e "s|HEAD is||g" -e 's|^|\t|g'
        echo
    fi
}

for repo_path in ${PYTHONPATH}/*;
do
    repo=`echo ${repo_path} | sed -e "s|${PYTHONPATH}/||g"`
    if [ $repo != "al_services" ]; then
        switch_branch ${repo_path} ${repo}
    fi
done

for repo_path in ${PYTHONPATH}/al_services/*;
do
    repo=`echo ${repo_path} | sed -e "s|${PYTHONPATH}/al_services/||g"`
    switch_branch ${repo_path} $repo
done
