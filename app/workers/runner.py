"""RQ worker entrypoint: python -m app.workers.runner"""

import logging

from rq import Worker

from app.core.logging import configure_logging
from app.workers.queue import get_queue

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    queue = get_queue()
    worker = Worker([queue], connection=queue.connection)
    logger.info("Starting RQ worker on queue 'default'")
    worker.work()


if __name__ == "__main__":
    main()
