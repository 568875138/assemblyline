#!/usr/bin/env python

import os
import subprocess
import sys

sys.path.append(os.path.realpath(__file__).replace('assemblyline/al/run/setup_dev_environment.py', ''))

if __name__ == "__main__":
    from assemblyline.al.install import SiteInstaller

    # noinspection PyBroadException
    try:
        proc = subprocess.Popen(["git", "remote", "-v"],
                                cwd=os.path.dirname(os.path.realpath(__file__)),
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        rem_stdout, _ = proc.communicate()
        proc = subprocess.Popen(["git", "branch"],
                                cwd=os.path.dirname(os.path.realpath(__file__)),
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        br_stdout, _ = proc.communicate()

        git_override = {
            'url': rem_stdout.split("\n", 1)[0].split("\t", 1)[1].rsplit(" ", 1)[0].replace("/assemblyline", "/{repo}"),
            'branch': br_stdout.split("* ")[1].split("\n")[0]
        }
    except Exception, e:
        git_override = None

    args = sys.argv[1:]
    if not args:
        seed = 'assemblyline.al.install.seeds.assemblyline_common.DEFAULT_SEED'
    else:
        seed = args[0]

    ssi = SiteInstaller(seed=seed, simple=True)
    ssi.setup_git_repos(git_override=git_override)
