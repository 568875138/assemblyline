from assemblyline.common.importing import class_by_name
from assemblyline.al.common import forge

store = forge.get_datastore()


def service_by_name(n):
    service = store.get_service(n)
    return class_by_name(service['classpath'])
