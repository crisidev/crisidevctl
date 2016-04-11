import os
import time
import stat
import json
import logging
import tempfile
import bisect
import requests
from dns import resolver
from jinja2 import Template
from pprint import pformat
from ..shell import runcmd
from ..config import cfg
from ..etcdclient import CrisidevEtcd
from ..exceptions import CrisidevException

logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


class CrisidevClusterLB(object):
    def __init__(self, args):
        self.keys = None
        self.tcp = {}
        self.udp = {}
        self.used_ports = []
        self.gorb_status = {}
        self.gorb_former_status = {}
        self.gorb_to_remove = {}
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
                    k = key.key.split("/")[-1]
                    v = json.loads(key.value)
                    if v.get('gorb'):
                        self._setup_gorb_mapping(k, v.get('gorb'))
            except IndexError:
                break
        # log.info("gorb mapping: " + pformat(self.gorb_status))
        # log.info("iptables tcp mapping: {}".format(self.tcp))
        # log.info("iptables udp mapping: {}".format(self.udp))
        self._read_gorb_status_from_etcd()

    def _write_gorb_status_on_etcd(self):
        log.info("gorb new status: {}".format(self.gorb_status))
        self.etcd.write(cfg.etcd_gorb_status_path, self.gorb_status)

    def _read_gorb_status_from_etcd(self):
        try:
            self.gorb_former_status = eval(self.etcd.read_single(cfg.etcd_gorb_status_path).value)
        except AttributeError:
            self.gorb_former_status = {}
        log.info("gorb former status: {}".format(self.gorb_former_status))

    def _add_port_to_used_ports(self, port):
        bisect.insort(self.used_ports, port)

    def _setup_gorb_mapping(self, hostname, gorb):
        lb_mapping = {}
        self.tcp[hostname] = []
        self.udp[hostname] = []
        for count, lb_port in enumerate(gorb['lb_ports']):
            backend_mapping = []
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
            if gorb.get("persistent") == "false":
                persistent = False
            elif gorb.get("persistent") == "true":
                persistent = True
            else:
                persistent = cfg.gorb_default_lb_persistent
            lb_mapping = {
                "host": gorb.get('lb_vip') or cfg.gorb_default_lb_vip,
                "port": port,
                "protocol": proto,
                "method": gorb.get('lb_method') or cfg.gorb_default_lb_method,
                "persistent": persistent,
            }
            backends = resolver.query(hostname, 'A')
            weight = int(100 / len(backends))
            for ip in backends:
                backend_port, backend_proto = gorb.get('backend_ports')[count].split('/')
                mapping = {
                    "host": ip.address,
                    "port": int(backend_port),
                    "method": gorb.get('backend_method') or cfg.gorb_default_backend_method,
                    "weight": weight,
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
            lb_name = "{}-{}".format(hostname, port)
            self.gorb_status[lb_name] = {
                "lb": lb_mapping,
                "backends": backend_mapping
            }

    def _update_gorb_to_remove(self):
        for lb_name, value in sorted(self.gorb_former_status.iteritems()):
            if lb_name not in self.gorb_status.keys():
                self.gorb_to_remove[lb_name] = []
            else:
                for backend in value['backends']:
                    if backend not in self.gorb_status[lb_name]['backends']:
                        if not self.gorb_to_remove.get(lb_name):
                            self.gorb_to_remove[lb_name] = ["{}-{}".format(backend.get('host'), backend.get('port'))]
                        else:
                            self.gorb_to_remove[lb_name].append("{}-{}".format(backend.get('host'),
                                                                               backend.get('port')))
        log.info("lbs to remove from gorb: {}".format(pformat(self.gorb_to_remove)))

    def _cleanup_gorb(self):
        self._update_gorb_to_remove()
        for lb_name, value in sorted(self.gorb_to_remove.iteritems()):
            if value == []:
                self._delete(lb_name)
            else:
                for backend in value:
                    backend_name = "{}/{}".format(lb_name, backend)
                    self._delete(backend_name)

    def _update_gorb(self):
        self._cleanup_gorb()
        for lb_name, value in sorted(self.gorb_status.iteritems()):
            status_code, response = self._get(lb_name)
            if status_code == 404:
                log.info("creating lb {}, method".format(lb_name, value['lb']['method']))
                self._put(lb_name, value["lb"])
            elif response['options']['host'] != value["lb"]['host'] or \
                    response['options']['port'] != value["lb"]['port'] or \
                    response['options']['protocol'] != value["lb"]['protocol'] or \
                    response['options']['persistent'] != value["lb"]['persistent'] or \
                    response['options']['method'] != value["lb"]['method']:
                log.info("updating lb {}".format(lb_name))
                self._delete(lb_name)
                time.sleep(1)
                self._put(lb_name, value["lb"])
            for backend in value["backends"]:
                backend_name = "{}/{}-{}".format(lb_name, backend.get("host"), backend.get('port'))
                status_code, response = self._get(backend_name)
                if status_code == 404:
                    log.info("creating backend {} for {}, method {}".format(backend['host'], lb_name,
                                                                            backend['method']))
                    self._put(backend_name, backend)
                elif response['options']['host'] != backend['host'] or \
                        response['options']['port'] != backend['port'] or \
                        response['options']['method'] != backend['method']:
                    log.info("updating backend {} for {}, method {}".format(backend['host'], lb_name,
                                                                            backend['method']))
                    self._delete(backend_name, backend)
                    time.sleep(1)
                    self._patch(backend_name, backend)
                elif response['options']['weight'] != backend['weight']:
                    log.info("updating backend {} for {}, weight {}".format(backend['host'], lb_name,
                                                                            backend['weight']))
                    self._patch(backend_name, backend)
        self._write_gorb_status_on_etcd()

    def _get(self, service):
        url = "{}/{}".format(cfg.gorb_endpoint, service)
        r = requests.get(url, headers=self.header)
        if r.status_code not in (200, 404):
            log.error("requests get error url {}: {} ".format(url, r.status_code))
        return r.status_code, r.json()

    def _delete(self, service):
        url = "{}/{}".format(cfg.gorb_endpoint, service)
        r = requests.delete(url, headers=self.header)
        if not r.status_code == 200:
            log.error("requests delete url {}: {} ".format(url, r.status_code))
        return r.status_code

    def _put(self, service, content):
        url = "{}/{}".format(cfg.gorb_endpoint, service)
        r = requests.put(url, data=json.dumps(content), headers=self.header)
        if r.status_code != 200:
            log.error("requests put error url {}: {} ".format(url, r.status_code) + pformat(content))
        return r.status_code

    def _patch(self, service, content):
        url = "{}/{}".format(cfg.gorb_endpoint, service)
        r = requests.patch(url, data=json.dumps(content), headers=self.header)
        if r.status_code != 200:
            log.error("requests patch error url {}: {} ".format(url, r.status_code) + pformat(content))
        return r.status_code

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
        runcmd("etcdctl rm {}".format(cfg.etcd_gorb_status_path))
        r, o, e = runcmd("systemctl restart {}".format(cfg.gorb_unit_file))
        if r:
            raise CrisidevException("firewall test failed, skipping reload")
        time.sleep(5)

    def do(self):
        if self.cleanup:
            self._restart_gorb()
        self._prepare_services_dict()
        self._update_gorb()
        self._write_firewall()
        self._restart_firewall()
