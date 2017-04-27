import uuid
from assemblyline.al.common import forge

ds = forge.get_datastore()

for alert in ds.get_user("__workflow___favorites")['alert']:
    ds.save_workflow(str(uuid.uuid4()), alert)
