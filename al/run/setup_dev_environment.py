#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.realpath(__file__).replace('assemblyline/al/run/setup_dev_environment.py', ''))

if __name__ == "__main__":
    from assemblyline.al.install import SiteInstaller

    args = sys.argv[1:]
    if not args:
        seed = 'assemblyline.al.install.seeds.assemblyline_common.DEFAULT_SEED'
    else:
        seed = args[0]

    ssi = SiteInstaller(seed=seed, simple=True)
    ssi.setup_git_repos()