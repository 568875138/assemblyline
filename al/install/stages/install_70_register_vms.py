#!/usr/bin/env python


def install(alsi=None):
    # shortly we will allow node specific service list override. 
    # for now they always get default.
    vms_to_register = alsi.config['workers']['virtualmachines']['master_list']
    alsi.info("Preparing to Register VMs: %s", ",".join(vms_to_register.keys()))

    from assemblyline.al.common import forge
    ds = forge.get_datastore()

    # for now we assume VM name matches the service name that it should run
    for vm_name, vm_details in vms_to_register.iteritems():
        try:
            vm_cfg = vm_details['cfg']
            ds.save_virtualmachine(vm_name, vm_cfg)
        except:
            alsi.fatal("Failed to register VM %s." % vm_name)
            alsi.log.exception('While registering VM %s', vm_name)


if __name__ == '__main__':
    from assemblyline.al.install import SiteInstaller
    installer = SiteInstaller()
    install(installer)
