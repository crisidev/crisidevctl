import logging

from etcd import Client, EtcdKeyNotFound, EtcdConnectionFailed

from config import cfg
from exceptions import CrisidevException

log = logging.getLogger(__name__)


class CrisidevEtcd(object):
    def __init__(self):
        self.client = self._get_etcd_client()

    def _get_etcd_client(self):
        return Client(host=cfg.etcd_host, port=cfg.etcd_port)

    def read(self, path):
        log.info("retrieving keys under {} from etcd".format(path))
        try:
            return self.client.get(path).children
        except EtcdKeyNotFound:
            raise CrisidevException("error reading etcd key, key not found")
        except EtcdConnectionFailed:
            raise CrisidevException("error reading etcd key, {} unreachable".format(cfg.etcd_host))
