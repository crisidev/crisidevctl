import os
import urllib2
import tempfile
import logging
from functools import partial
from multiprocessing.dummy import Pool
from jinja2 import Template

from ..shell import runcmd
from ..config import cfg
from ..exceptions import CrisidevException

log = logging.getLogger(__name__)


class CrisidevClusterInit(object):

    def __init__(self, args):
        self.etcd_key = None
        self.password_hash = None
        self.ssh_private_key = None
        self.ssh_public_key = None
        self.config_dict = {}
        self.used_ndbs = []
        self.dry_run = args.dry_run
        self.ssh_priv_key = args.ssh_priv_key
        self.ssh_pub_key = args.ssh_pub_key
        self.renew_etcd = args.renew_etcd
        self.domain = args.domain
        self.cluster = args.cluster
        if os.path.exists(args.cloud_config):
            self.cloud_config = args.cloud_config
        else:
            raise CrisidevException("cloud init %s config file not found" % args.cloud_config)
        self.addresses = [x.strip() for x in args.addresses.split(",")]
        self.dns_names = self._analyze_dns_names(args.dns_names)
        if len(self.dns_names) != len(self.addresses):
            raise CrisidevException("parameters --dns_names and --addresses have different members number")
        log.info("initialising {} new VM disks".format(len(self.dns_names)))
        self.disk_size = int(args.disk_size)

    def __call__(self):
        self.do()

    def _analyze_dns_names(self, input_list):
        tokens = input_list.split(",")
        tokens = [x.strip() for x in tokens]
        for token in tokens:
            if self.domain not in token:
                raise CrisidevException("domain name %s and hostname %s does not match" % (self.domain, token))
        return tokens

    def _read_etcd_key(self):
        if not os.path.exists(cfg.etcd_keyfile):
            try:
                os.makedirs(os.path.dirname(cfg.etcd_keyfile))
            except OSError:
                pass
            self._renew_etcd_key()
        else:
            with open(cfg.etcd_keyfile) as fd:
                self.etcd_key = fd.read()
        log.info("etcd key used: {}".format(self.etcd_key))

    def _renew_etcd_key(self):
        self.etcd_key = self._get_etcd_key()
        self._write_config_etcd_key()

    def _get_etcd_key(self):
        data = urllib2.urlopen(cfg.etcd_discovery)
        etcd_key = data.read()
        log.info("got new etcd key {} from {}".format(etcd_key, cfg.etcd_discovery))
        return etcd_key

    def _write_config_etcd_key(self):
        log.info("writing etcd key {} to {}".format(self.etcd_key, cfg.etcd_keyfile))
        with open(cfg.etcd_keyfile, "w") as fd:
            fd.write(self.etcd_key)

    def _create_vm_disk(self, name):
        shortname = name.split(".")[0]
        disk_path = os.path.join("/dev/mapper", "{}-{}".format(cfg.kvm_vg_name, shortname))
        if not os.path.exists(disk_path):
            if self.disk_size:
                log.info("disk {} not found. creating a new one, size {} Gb".format(disk_path, self.disk_size))
                runcmd("sudo lvcreate -L {}GiB -n {} {}".format(self.disk_size, shortname, cfg.kvm_vg_name))
            else:
                raise CrisidevException("--disk_size option required for new disks")
        else:
            log.info("disk {} already present. overriding with new image".format(disk_path))
        return disk_path

    def _get_password_hash(self):
        if not self.password_hash:
            log.warning("please enter the password for `coreos` user on this cluster")
            r, o, e = runcmd("mkpasswd --method=SHA-512 --rounds=4096")
            if r:
                raise CrisidevException("unable to read passwd for etcd cluster")
            self.password_hash = o.strip()

    def _get_ssh_keys(self):
        log.info("trying to get the specified SSH keys")
        if os.path.exists(self.ssh_priv_key):
            with open(self.ssh_priv_key) as fd:
                self.ssh_private_key = fd.read()
        else:
            raise CrisidevException("ssh private key {} not found".format(self.ssh_priv_key))
        if os.path.exists(self.ssh_pub_key):
            with open(self.ssh_pub_key) as fd:
                self.ssh_public_key = fd.read()
        else:
            raise CrisidevException("ssh public key {} not found".format(self.ssh_pub_key))

    def _write_temp_cloud_config(self, hostname, address, filename):
        log.info("rendering cloud-config for {} to {}".format(hostname, filename))
        with open(self.cloud_config, "r") as fd:
            shortname = hostname.split(".")[0]
            flavour = ''.join([i for i in shortname if not i.isdigit()])
            template = Template(fd.read())
            render = template.render(hostname=hostname, address=address,
                                     shortname=shortname,
                                     domain=self.domain,
                                     cluster=self.cluster,
                                     flavour=flavour,
                                     etcd_key=self.etcd_key,
                                     password_hash=self.password_hash,
                                     ssh_public_key=self.ssh_public_key.strip("\n"),
                                     ssh_private_key=self.ssh_private_key)
            with open(filename, "w") as fd:
                fd.write(render)

    def _install_coreos(self):
        commands = []
        log.info(self.config_dict)
        for key, value in self.config_dict.iteritems():
            log.info("installing coreos on {}".format(value['disk']))
            commands.append("coreos-install -v -d {} -C {} -c {}".format(value['disk'],
                            cfg.coreos_update_channel, value['tmpfile']))
        pool = Pool(len(self.dns_names))
        for i, retval in enumerate(pool.imap(partial(runcmd), commands)):
            if retval[0]:
                log.error("%s command failed: %s" % (i, retval[2]))

    def _cleanup(self):
        log.info("cleaning up temporary files")
        for _, value in self.config_dict.iteritems():
            runcmd("sudo kpartx -d {}".format(value['disk']))
            if not self.dry_run:
                os.remove(value['tmpfile'])

    def do(self):
        try:
            self._get_password_hash()
            self._get_ssh_keys()
            if self.renew_etcd:
                self._renew_etcd_key()
            self._read_etcd_key()
            for hostname in self.dns_names:
                self.config_dict[hostname] = {}
                log.info("building VM image for {}".format(hostname))
                tmpfile = tempfile.mktemp()
                self.config_dict[hostname]['tmpfile'] = tmpfile
                address = self.addresses[self.dns_names.index(hostname)]
                self._write_temp_cloud_config(hostname, address, tmpfile)
                self.config_dict[hostname]['disk'] = self._create_vm_disk(hostname)
            if not self.dry_run:
                self._install_coreos()
        except KeyboardInterrupt:
            self._cleanup()
        else:
            self._cleanup()
