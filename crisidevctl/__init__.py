import sys
import logging

from .parser import CrisidevCtl
from .exceptions import CrisidevException


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(name)-25s %(levelname)-6s %(process)s: %(message)s")
    log = logging.getLogger(__name__)
    try:
        CrisidevCtl()
    except CrisidevException as e:
        log.exception(e)
        sys.exit(1)
    else:
        sys.exit(0)
