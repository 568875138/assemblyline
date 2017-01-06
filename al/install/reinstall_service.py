#!/usr/bin/env python

import sys
import importlib
import os

from assemblyline.al.install import SiteInstaller
from assemblyline.al.install.stages import cmd_service_all

alsi = SiteInstaller()

service = None
try:
    service = sys.argv[1]
    if service not in alsi.config['services']['master_list']:
        alsi.error("Cannot find service '%s' in master service list" % service)
        exit(1)
except:
    alsi.error("Failed to install %s." % service or "(No service specified)")
    exit(1)

alsi.milestone("Stoping components")
cmd_service_all(alsi, 'stop')

alsi.milestone("Setting permissions on AL Root directory")
from assemblyline.al.install.stages import install_00_init
install_00_init.install(alsi)

service_detail = alsi.config['services']['master_list'][service]
classpath = service_detail['classpath'] or "al_services.%s.%s" % (service_detail['repo'], service_detail['class_name'])
config_overrides = service_detail.get('config', {})
service_directory = classpath.rpartition('.')[0]
installer_path = '.'.join([service_directory, 'installer'])
alsi.milestone("Installing %s using %s" % (service, installer_path))
try:
    m = importlib.import_module(installer_path)
    install_svc = getattr(m, 'install')
    install_svc(alsi)
except:
    alsi.error("Failed to install service %s." % service)
    alsi.log.exception('While installing service %s', service)

alsi.milestone("Cleaning up")
from assemblyline.al.install.stages import install_90_cleanup
install_90_cleanup.install(alsi)

if not os.getenv("AL_SEED_STATIC", None):
    # If not in static seed mode
    alsi.milestone("Starting components")
    cmd_service_all(alsi, 'stop')
    cmd_service_all(alsi, 'start')

alsi.milestone("Completed.")
