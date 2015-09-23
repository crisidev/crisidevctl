import os
import stat
import json
import logging
import tempfile
import bisect

from jinja2 import Template

from ..shell import runcmd
from ..config import cfg
from ..etcdclient import CrisidevEtcd
from ..exceptions import CrisidevException

log = logging.getLogger(__name__)


class CrisidevClusterNat(object):
    def __init__(self, args):
        self.keys = None
        self.tcp = {}
        self.udp = {}
        self.used_ports = []
        self.etcd_dir = args.etcd_dir or cfg.etcd_dir_crisidev
        self.bridge = args.bridge or cfg.vbox_bridge
        log.info("loading new NAT configuration")

    def __call__(self):
        self.etcd = CrisidevEtcd()
        log.info("reading directory {} from etcd".format(self.etcd_dir))
        self.keys = self.etcd.read(self.etcd_dir)
        self.do()

    def _prepare_services_dict(self):
        log.info("preparing dict for firewall template")
        for key in self.keys:
            try:
                if key.value:
                    k = key.key.split("/")[2]
                    v = json.loads(key.value)
                    if v.get('tcp'):
                        self.tcp[k] = self._setup_port_mapping(k, v.get('tcp'))
                    if v.get('udp'):
                        self.udp[k] = self._setup_port_mapping(k, v.get('udp'))
            except IndexError:
                break
        log.info("tcp mapping: {}".format(self.tcp))
        log.info("udp mapping: {}".format(self.udp))

    def _add_port_to_used_ports(self, port):
        bisect.insort(self.used_ports, port)

    def _get_starting_port(self, port):
        return cfg.nat_port_mapping.get(port) or port

    def _setup_port_mapping(self, hostname, ports):
        mapping = []
        for port in ports:
            if hostname in cfg.nat_reserved_ports and cfg.nat_reserved_ports[hostname][0] == port:
                extport = cfg.nat_reserved_ports[hostname][1]
            elif isinstance(port, unicode):
                extport = port
                port = port.replace(":", "-")
            else:
                extport = self._get_starting_port(port)
            while extport in self.used_ports:
                log.info("port {} already used, trying next one".format(extport))
                if extport >= 65535:
                    log.error("WTF!! no ports free")
                    break
                extport += 1
            self._add_port_to_used_ports(extport)
            mapping.append((port, extport))
        return mapping

    def _write_firewall(self):
        tmp = tempfile.mktemp()
        log.info("rendering template {} on {}".format(cfg.firewall_template, tmp))
        with open(cfg.firewall_template, "r") as fd:
            template = Template(fd.read())
            render = template.render(tcp=self.tcp, udp=self.udp, bridge=self.bridge)
            with open(tmp, "w") as fd:
                fd.write(render)
        log.info("moving {} to {}".format(tmp, cfg.firewall_file))
        os.rename(tmp, cfg.firewall_file)
        st = os.stat(cfg.firewall_file)
        os.chmod(cfg.firewall_file, st.st_mode | stat.S_IEXEC)

    def _restart_firewall(self):
        log.info("checking firewall scritp before restart")
        r, o, e = runcmd("bash -n {}".format(cfg.firewall_file))
        if r:
            raise CrisidevException("firewall test failed, skipping reload")
        r, o, e = runcmd("bash {}".format(cfg.firewall_file))
        if r:
            log.error("firewall failed, loading default one from {}".format(
                      cfg.firewall_file_safe))
            runcmd("bash {}".format(cfg.firewall_file_safe))

    def do(self):
        self._prepare_services_dict()
        self._write_firewall()
        self._restart_firewall()
