import json
import logging

from pprint import pformat

from ..config import cfg
from ..etcdclient import CrisidevEtcd

log = logging.getLogger(__name__)


class CrisidevClusterProm(object):
    def __init__(self, args):
        self.prom = {}
        self.etcd_dir = args.etcd_dir or cfg.etcd_dir_prometheus
        self.prom_file = args.prom_file or cfg.prometheus_targets_file

    def __call__(self):
        self.etcd = CrisidevEtcd()
        log.info("reading directory {} from etcd".format(self.etcd_dir))
        self.keys = sorted(self.etcd.read(self.etcd_dir), key=lambda x: x.key)
        self.do()

    def _prepare_services_dict(self):
        log.info("preparing dict for prometheus template")
        for key in self.keys:
            try:
                if key.value:
                    k = key.key.split("/")[-1]
                    k_split = k.split(".")
                    v = json.loads(key.value)
                    service = "{}.{}.{}".format(k_split[-3], k_split[-2], k_split[-1])
                    if self.prom.get(service):
                        self.prom[service].append("{}:{}".format(k, v))
                    else:
                        self.prom[service] = ["{}:{}".format(k, v)]
            except IndexError:
                break
        log.info("prom mapping:\n{}".format(pformat(self.prom)))

    def _update_prometheus_targets(self):
        with open(self.prom_file, 'w') as fd:
            for group, value in self.prom.iteritems():
                fd.write("- targets:\n")
                for target in value:
                    fd.write("  - '{}'\n".format(target))
                fd.write("  labels:\n")
                fd.write("    cluster: 'crisidev'\n")
                fd.write("    job: '{}'\n".format(group))

    def do(self):
        self._prepare_services_dict()
        self._update_prometheus_targets()
