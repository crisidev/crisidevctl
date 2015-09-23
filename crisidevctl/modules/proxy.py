import os
import json
import tempfile
import logging
from jinja2 import Template

from ..shell import runcmd
from ..config import cfg
from ..etcdclient import CrisidevEtcd
from ..exceptions import CrisidevException

log = logging.getLogger(__name__)


class CrisidevClusterProxy(object):
    def __init__(self, args):
        self.keys = None
        self.http = {}
        self.https = {}
        self.etcd_dir = args.etcd_dir or cfg.etcd_dir_crisidev
        log.info("loading new Nginx Proxy configuration")

    def __call__(self):
        self.etcd = CrisidevEtcd()
        log.info("reading directory {} from etcd".format(self.etcd_dir))
        self.do()

    def _prepare_services_dict(self, flavour):
        log.info("preparing {} dict for nginx template".format(flavour))
        keys = self.etcd.read(self.etcd_dir)
        service_dict = {}
        for key in keys:
            if key.value:
                v = json.loads(key.value)
                if v.get(flavour):
                    k = key.key.split("/")[2]
                    service_dict[k] = {"ports": v.get(flavour), "htaccess": v.get("htaccess")}
        log.info("{} mapping: {}".format(flavour, service_dict))
        setattr(self, flavour, service_dict)

    def _write_nginx_config(self, flavour):
        tmp = tempfile.mktemp()
        nginx_template = cfg.nginx_template.format(flavour)
        nginx_config_file = cfg.nginx_config_file.format(flavour)
        log.info("rendering template {} on {}".format(nginx_template, tmp))
        with open(nginx_template, "r") as fd:
            template = Template(fd.read())
            render = template.render(services=getattr(self, flavour))
            with open(tmp, "w") as fd:
                fd.write(render)
        log.info("moving {} to {}".format(tmp, nginx_config_file))
        os.rename(tmp, nginx_config_file)

    def _restart_nginx(self):
        log.info("checking nginx configuration before reload")
        r, o, e = runcmd("nginx -t")
        if r:
            raise CrisidevException("nginx test configuration failed, skipping reload")
        runcmd("service nginx reload")

    def do(self):
        for flavour in ("http", "https"):
            self._prepare_services_dict(flavour)
            self._write_nginx_config(flavour)
        self._restart_nginx()
