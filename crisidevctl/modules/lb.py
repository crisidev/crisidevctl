import os
import time
import stat
import json
import logging
import tempfile
import collections
import bisect
import sys

import requests
logging.getLogger("urllib3").setLevel(logging.WARNING)

from dns import resolver
from jinja2 import Template
from pprint import pformat

from ..shell import runcmd
from ..config import cfg
from ..etcdclient import CrisidevEtcd
from ..exceptions import CrisidevException

log = logging.getLogger(__name__)


class CrisidevClusterLB(object):
    def __init__(self, args):
        self.keys = None
        self.tcp = {}
        self.udp = {}
        self.gorb = collections.OrderedDict()
        self.used_ports = []
        self.used_lbs = []
        self.former_used_lbs = []
        self.header = {"content-type": "application/json"}
        self.etcd_dir = args.etcd_dir or cfg.etcd_dir_crisidev
        self.bridge = args.bridge or cfg.kvm_bridge
        self.cleanup = args.cleanup
        log.info("loading new NAT configuration")

    def __call__(self):
        self.etcd = CrisidevEtcd()
        log.info("reading directory {} from etcd".format(self.etcd_dir))
        self.keys = sorted(self.etcd.read(self.etcd_dir), key=lambda x: x.key)
        self.do()

    def _prepare_services_dict(self):
        log.info("preparing dict for firewall template")
        for key in self.keys:
            try:
                if key.value:
                    k = key.key.split("/")[2]
                    print key.value
                    v = json.loads(key.value)
                    if v.get('gorb'):
                        lb, backends = self._setup_gorb_mapping(k, v.get('gorb'))
                        self.gorb[k] = {
                            'lb': lb,
                            'backends': backends
                        }
            except IndexError:
                break
        log.info("gorb mapping: " + pformat(self.gorb))
        log.info("iptables tcp mapping: {}".format(self.tcp))
        log.info("iptables udp mapping: {}".format(self.udp))
        self._read_used_lbs_on_etcd()

    def _write_used_lbs_on_etcd(self):
        log.info("gorb used lbs: {}".format(self.used_lbs))
        self.etcd.write(cfg.etcd_gorb_lbs_path, self.used_lbs)

    def _read_used_lbs_on_etcd(self):
        try:
            self.former_used_lbs = eval(self.etcd.read_single(cfg.etcd_gorb_lbs_path).value)
        except AttributeError:
            self.former_used_lbs = []
        log.info("gorb former used lbs: {}".format(self.former_used_lbs))

    def _add_port_to_used_ports(self, port):
        bisect.insort(self.used_ports, port)

    def _add_lb_to_used_lbs(self, lb):
        bisect.insort(self.used_lbs, lb)

    def _setup_gorb_mapping(self, hostname, gorb):
        lb_mapping = {}
        backend_mapping = []
        self.tcp[hostname] = []
        self.udp[hostname] = []
        for count, lb_port in enumerate(gorb['lb_ports']):
            if lb_port in cfg.nat_reserved_ports:
                lb_port = cfg.nat_reserved_ports[lb_port]
            port, proto = lb_port.split('/')
            port = int(port)
            while lb_port in self.used_ports:
                log.info("port {} already used, trying next one".format(lb_port))
                if port >= 65535:
                    log.error("WTF!! no ports free")
                    break
                port += 1
                lb_port = "{}/{}".format(port, proto)
            self._add_port_to_used_ports(lb_port)
            lb_mapping = {
                "host": gorb.get('lb_vip') or cfg.gorb_default_lb_vip,
                "port": port,
                "protocol": proto,
                "method": gorb.get('lb_method') or cfg.gorb_default_lb_method,
                "persistent": gorb.get('persistent') or cfg.gorb_default_lb_persistent,
            }
            for ip in resolver.query(hostname, 'A'):
                backend_port, backend_proto = gorb.get('backend_ports')[count].split('/')
                mapping = {
                    "host": ip.address,
                    "port": int(backend_port),
                    "method": gorb.get('backend_method') or cfg.gorb_default_backend_method,
                }
                if proto == "udp":
                    mapping['pulse'] = {
                        'type': 'none'
                    }
                backend_mapping.append(mapping)
            if proto == "tcp":
                self.tcp[hostname].append((backend_port, port))
            if proto == "udp":
                self.udp[hostname].append((backend_port, port))
        self._add_lb_to_used_lbs(hostname)
        return lb_mapping, backend_mapping

    def _cleanup_gorb(self):
        lbs_to_cleanup = set(self.former_used_lbs).difference(self.used_lbs)
        log.info("lbs to cleanup: {}".format(list(lbs_to_cleanup)))
        for lb in lbs_to_cleanup:
            log.info("removing outdated service {}".format(lb))
            response = self._delete(lb)
            if response == 404:
                log.error("lb {} removal failed. readded to used_lbs. please check".format(lb))
                self._add_lb_to_used_lbs(lb)
        self._write_used_lbs_on_etcd()

    def _update_gorb(self):
        self._cleanup_gorb()
        for lb, value in sorted(self.gorb.iteritems()):
            status_code, response = self._get(lb)
            if status_code == 404:
                log.info("creating service {}".format(lb))
                self._put(lb, value['lb'])
            elif response['options']['host'] != value['lb']['host'] or \
                    response['options']['port'] != value['lb']['port'] or \
                    response['options']['protocol'] != value['lb']['protocol'] or \
                    response['options']['persistent'] != value['lb']['persistent'] or \
                    response['options']['method'] != value['lb']['method']:
                log.info("updating service {}".format(lb))
                # log.warn("host: {} {}".format(response['options']['host'], value['lb']['host']))
                # log.warn("port: {} {}".format(response['options']['port'], value['lb']['port']))
                # log.warn("proto: {} {}".format(response['options']['protocol'], value['lb']['protocol']))
                # log.warn("persistent: {} {}".format(response['options']['persistent'], value['lb']['persistent']))
                # log.warn("method: {} {}".format(response['options']['method'], value['lb']['method']))
                self._delete(lb)
                time.sleep(10)
                self._put(lb, value['lb'])
            for backend in value['backends']:
                service = "{}/{}".format(lb, backend['host'])
                status_code, response = self._get(service)
                if status_code == 404:
                    log.info("creating backend {} for {}".format(backend['host'], lb))
                    self._put(service, backend)
                elif response['options']['host'] != backend['host'] or \
                        response['options']['port'] != backend['port'] or \
                        response['options']['method'] != backend['method']:
                    log.info("updating backend {} for {}".format(backend['host'], lb))
                    self._delete(service)
                    time.sleep(10)
                    self._put(service, backend)

    def _get(self, service):
        r = requests.get("{}/{}".format(cfg.gorb_endpoint, service), headers=self.header)
        log.info("get {}/{}: {}".format(cfg.gorb_endpoint, service, r.status_code))
        return r.status_code, r.json()

    def _delete(self, service):
        r = requests.delete("{}/{}".format(cfg.gorb_endpoint, service), headers=self.header)
        log.info("delete {}/{}: {}".format(cfg.gorb_endpoint, service, r.status_code))
        return r.status_code

    def _put(self, service, content):
        r = requests.put("{}/{}".format(cfg.gorb_endpoint, service), data=json.dumps(content), headers=self.header)
        log.info("put {}/{}: {}".format(cfg.gorb_endpoint, service, r.status_code))
        if r.status_code != 200:
            log.error("put error: {}\n".format(r.status_code) + pformat(content))
        return r.status_code

    def _patch(self, service, content):
        r = requests.patch("{}/{}".format(cfg.gorb_endpoint, service), data=json.dumps(content), headers=self.header)

    def _write_firewall(self):
        tmp = tempfile.mktemp()
        log.info("rendering firewall template {} on {}".format(cfg.firewall_template, tmp))
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

    def _restart_gorb(self):
        log.info("cleanup requested. cleaning up etcd and restarting gorb")
        runcmd("etcdctl rm {}".format(cfg.etcd_gorb_lbs_path))
        r, o, e = runcmd("systemctl restart {}".format(cfg.gorb_unifile))
        if r:
            raise CrisidevException("firewall test failed, skipping reload")


    def do(self):
        if self.cleanup:
            self._restart_gorb()
        self._prepare_services_dict()
        self._update_gorb()
        self._write_firewall()
        self._restart_firewall()
