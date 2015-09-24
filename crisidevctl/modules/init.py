import os
import urllib2
import tempfile
import logging
from random import randint
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
        if os.path.exists(args.cloud_config):
            self.cloud_config = args.cloud_config
        else:
            raise CrisidevException("cloud init %s config file not found" % args.cloud_config)
        self.dns_names = self._analyze_input_list(args.dns_names)
        self.addresses = self._analyze_input_list(args.addresses)
        if len(self.dns_names) != len(self.addresses):
            raise CrisidevException("parameters --dns_names and --addresses have different members number")
        log.info("initialising {} new VM disks".format(len(self.dns_names)))
        self.disk_size = int(args.disk_size)

    def __call__(self):
        self.do()

    def _analyze_input_list(self, input_list):
        tokens = input_list.split(",")
        tokens = [x.strip() for x in tokens]
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

    def _create_vbox_disk(self, name):
        disk_path = os.path.join(cfg.kvm_disk_path, "{}.raw".format(name))
        if not os.path.exists(disk_path):
            if self.disk_size:
                log.info("disk {} not found. creating a new one, size {} Gb".format(disk_path, self.disk_size))
                runcmd("sudo -u {} qemu-img create -f raw -o size={}G {}".format(
                    cfg.kvm_user, self.disk_size, disk_path))
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

    def _write_temp_cloud_config(self, hostname, address, filename, enable_fleetui):
        log.info("rendering cloud-config for {} to {}".format(hostname, filename))
        with open(self.cloud_config, "r") as fd:
            shortname = hostname.split(".")[0]
            flavour = ''.join([i for i in shortname if not i.isdigit()])
            template = Template(fd.read())
            render = template.render(hostname=hostname, address=address,
                                     shortname=shortname,
                                     flavour=flavour,
                                     etcd_key=self.etcd_key,
                                     password_hash=self.password_hash,
                                     ssh_public_key=self.ssh_public_key.strip("\n"),
                                     ssh_private_key=self.ssh_private_key,
                                     enable_fleetui=enable_fleetui)
            with open(filename, "w") as fd:
                fd.write(render)

    def _find_free_nbd(self, hostname):
        log.info("searching for a free NBD device in the first 10")
        for x in xrange(10):
            r, o, e = runcmd("nbd-client -c /dev/ndb{}".format(x))
            if r:
                nbd = "/dev/nbd{}".format(x)
                if nbd not in self.used_ndbs:
                    self.used_ndbs.append(nbd)
                    return nbd
        raise CrisidevException("no free NBD device found")

    def _mount_nbd(self, disk_path, nbd):
        log.info("connecting {} to {}".format(disk_path, nbd))
        r, o, e = runcmd("qemu-nbd -c {} {}".format(nbd, disk_path))
        if r:
            raise CrisidevException("unable to connect {} to {}".format(disk_path, nbd))

    def _umount_nbd(self, nbd):
        log.info("disconnecting {}".format(nbd))
        runcmd("qemu-nbd -d {}".format(nbd))

    def _install_coreos(self):
        commands = []
        for key, value in self.config_dict.iteritems():
            log.info("installing coreos on {}".format(value['nbd']))
            commands.append("coreos-install -d {} -C {} -c {}".format(value['nbd'],
                            cfg.coreos_update_channel, value['tmpfile']))
        pool = Pool(len(self.dns_names))
        for i, retval in enumerate(pool.imap(partial(runcmd), commands)):
            if retval[0]:
                log.error("%s command failed: %s" % (i, retval[2]))

    def _cleanup(self):
        log.info("cleaning up used NBD devices")
        for _, value in self.config_dict.iteritems():
            self._umount_nbd(value['nbd'])
            if not self.dry_run:
                os.remove(value['tmpfile'])

    def do(self):
        fleetui_host_number = randint(0, len(self.dns_names))
        try:
            self._get_password_hash()
            self._get_ssh_keys()
            if self.renew_etcd:
                self._renew_etcd_key()
            self._read_etcd_key()
            for i, hostname in enumerate(self.dns_names):
                enable_fleetui = False
                self.config_dict[hostname] = {}
                log.info("building VM image for {}".format(hostname))
                tmpfile = tempfile.mktemp()
                self.config_dict[hostname]['tmpfile'] = tmpfile
                address = self.addresses[self.dns_names.index(hostname)]
                if fleetui_host_number == i:
                    enable_fleetui = True
                self._write_temp_cloud_config(hostname, address, tmpfile, enable_fleetui)
                disk_path = self._create_vbox_disk(hostname)
                nbd = self._find_free_nbd(hostname)
                self.config_dict[hostname]['nbd'] = nbd
                try:
                    self._mount_nbd(disk_path, nbd)
                except CrisidevException as e:
                    log.error(e)
                    self._umount_nbd(nbd)
                    self._mount_nbd(disk_path, nbd)
            if not self.dry_run:
                self._install_coreos()
        except KeyboardInterrupt:
            self._cleanup()
        else:
            self._cleanup()
