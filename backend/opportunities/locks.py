from django.conf import settings
from redis import Redis


_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


def opportunity_pipeline_redis_client():
    return Redis.from_url(settings.OPPORTUNITY_PIPELINE_LOCK_REDIS_URL, decode_responses=True)


def get_pipeline_lock_key(source):
    return f"pipeline:{source}:lock"


def acquire_pipeline_lock(client, lock_key, token, timeout=None):
    lock_timeout = timeout or settings.OPPORTUNITY_PIPELINE_LOCK_TIMEOUT
    return bool(client.set(lock_key, token, nx=True, ex=lock_timeout))


def release_pipeline_lock(client, lock_key, token):
    return bool(client.eval(_RELEASE_LOCK_SCRIPT, 1, lock_key, token))
