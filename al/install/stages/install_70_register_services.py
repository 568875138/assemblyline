#!/usr/bin/env python
from assemblyline.al.common.config_riak import load_seed, save_seed
from assemblyline.al.service import register_service


def install(alsi=None):
    # shortly we will allow node specific service list override. 
    # for now they always get default.
    services_to_register = alsi.config['services']['master_list']
    alsi.info("Preparing to Register: %s", services_to_register)

    for service, service_detail in services_to_register.iteritems():
        service_detail = alsi.config['services']['master_list'][service]
        classpath = service_detail['classpath']
        config_overrides = service_detail.get('config', {})

        # noinspection PyBroadException
        try:
            register_service.register(classpath, config_overrides=config_overrides,
                                      enabled=service_detail.get('enabled', True))
        except:
            alsi.fatal("Failed to register service %s." % service)
            alsi.log.exception('While registering service %s', service)

    seed = load_seed()
    save_seed(seed, "original_seed")
    save_seed(seed, "previous_seed")

if __name__ == '__main__':
    from assemblyline.al.install import SiteInstaller
    installer = SiteInstaller()
    install(installer)
