#!/usr/bin/env python

from assemblyline.al.install.seeds.assemblyline_appliance import seed

seed['monitoring']['harddrive'] = False
seed['workers']['install_kvm'] = False
seed['workers']['virtualmachines']['master_list'] = {}

if __name__ == '__main__':
    import sys

    if "json" in sys.argv:
        import json
        print json.dumps(seed)
    else:
        import pprint
        pprint.pprint(seed)
