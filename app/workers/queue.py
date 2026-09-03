import redis
from rq import Queue

from app.core.config import settings

_queue: Queue | None = None


def get_queue() -> Queue:
    global _queue
    if _queue is None:
        conn = redis.from_url(settings.redis_url)
        _queue = Queue("default", connection=conn)
    return _queue
