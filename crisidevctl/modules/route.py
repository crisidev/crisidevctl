import logging
import json

from ..shell import runcmd
from ..config import cfg
from ..etcdclient import CrisidevEtcd

log = logging.getLogger(__name__)


class CrisidevClusterRoute(object):
    def __init__(self, args):
        self.keys = None
        self.remove = args.remove
        self.bridge = args.bridge or cfg.vbox_bridge

    def __call__(self):
        self.etcd = CrisidevEtcd()
        log.info("reading subnets from etcd")
        self.keys = self.etcd.read(cfg.etcd_dir_coreos_subnet)
        self.do()

    def _iter_subnets(self):
        for key in self.keys:
            subnet = key.key.split("/")[-1].replace("-", "/")
            gateway = json.loads(key.value)
            gateway = gateway["PublicIP"]
            yield (subnet, gateway)

    def _add_route(self, subnet, gateway):
        log.info("adding route for {}, gateway {}, bridge {}".format(subnet, gateway, self.bridge))
        runcmd("ip route add {} via {} dev {}".format(subnet, gateway, self.bridge))

    def _del_route(self, subnet):
        log.info("removing route for {}, bridge {}".format(subnet, self.bridge))
        runcmd("ip route del {} dev {}".format(subnet, self.bridge), alert=False)

    def _update_routes(self):
        log.info("updating VMs subnet routes")
        for value in self._iter_subnets():
            self._del_route(value[0])
            if not self.remove:
                self._add_route(value[0], value[1])

    def do(self):
        self._update_routes()
