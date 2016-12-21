#!/usr/bin/env python

import json
import logging
import redis
import time

from assemblyline.common import isotime
from assemblyline.al.common import forge, log as al_log

al_log.init_logging("quota_sniper")
logger = logging.getLogger('assemblyline.quota_sniper')
logger.setLevel(logging.INFO)

config = forge.get_config()

client = redis.StrictRedis(host=config.core.redis.nonpersistent.host,
                           port=config.core.redis.nonpersistent.port,
                           db=config.core.redis.nonpersistent.db)

persist = redis.StrictRedis(host=config.core.redis.persistent.host,
                            port=config.core.redis.persistent.port,
                            db=config.core.redis.persistent.db)

time_diff = 60 * 5  # Anything older than 5 minutes...
quota_time_diff = 60 * 60  # Anything older than 1 hour...

while True:
    data = client.hgetall('c-tracker-quota')
    if data:
        for key, value in data.iteritems():
            epoch = isotime.local_to_epoch(json.loads(value))
            now = time.time()
            if now - epoch >= time_diff:
                user = key.split(" ")[0]
                client.hdel('c-tracker-quota', key)
                client.decr('quota-{user}'.format(user=user))
                logger.warning("API request: \"{key}\" was removed from ongoing "
                               "request because it reached the timeout.".format(key=key))
            else:
                logger.debug("{key} is ok. [{now} - {value} < {time_diff}]".format(key=key, now=now, value=epoch,
                                                                                   time_diff=time_diff))

    for key in persist.keys('submissions-*'):
        data = persist.hgetall(key)
        for sid, t in data.iteritems():
            epoch = isotime.iso_to_epoch(json.loads(t))
            now = time.time()
            if now - epoch >= quota_time_diff:
                user = key.split('-')[1]
                logger.warning(
                    'Quota item "{sid}" for user "{user}" was removed'.format(sid=sid, user=user)
                )
                persist.hdel(key, sid)

    time.sleep(5)
