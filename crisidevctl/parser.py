import os
import sys
import logging
import argparse

from .config import cfg
from .shell import which
from .modules.init import CrisidevClusterInit
from .modules.install import CrisidevClusterInstall
from .modules.route import CrisidevClusterRoute
from .modules.nat import CrisidevClusterNat
from .modules.proxy import CrisidevClusterProxy


class CrisidevCtl(object):

    def __init__(self):
        global cfg
        self.log = logging.getLogger(__name__)
        parser = argparse.ArgumentParser(
            description="Crisidev Cloud Control",
            usage="""crisidevctl <command> [<args>]

Commands:
   install          Install required files on the host machine
   init             Initialise VMs images for a new cluster
   route            Routes VMs subnet to allow inbound traffic
   nat              NAT containers tcp/udp ports on the public ip address
   proxy            Proxy containers http ports using nginx

""")
        parser.add_argument("command", help="Subcommand to run")
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            self.log.error("unrecognized command")
            parser.print_help()
            exit(1)
        if not os.geteuid() == 0:
            self.log.error('script must be run as root')
            exit(0)
        # use dispatch pattern to invoke method with same name
        retobj = getattr(self, args.command)()
        if self._check_dependencies():
            self.log.error("base crisidevctl dependencies not met")
            exit(1)
        retobj()

    def _check_dependencies(self):
        self.log.info("checking and crisidevctl base dependencies")
        retval = 0
        for command in cfg.dependencies.split(","):
            retval += which(command)
        return retval

    def install(self):
        return CrisidevClusterInstall()

    def init(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1],
                                         description="Initialise a new cluster a provided cloud-init template")
        # prefixing the argument with -- means it's optional
        parser.add_argument("-e", "--renew_etcd", dest="renew_etcd", required=False,
                            action="store_true", help="Renew etcd key for the cluster")
        parser.add_argument("-d", "--disk_size", dest="disk_size", required=False, default=0,
                            help="Size for new disks in GB")
        parser.add_argument("-c", "--cloud_config", dest="cloud_config", required=True, help="Cloud-config template")
        parser.add_argument("-n", "--dns_names", dest="dns_names", required=True,
                            help="List of hostnames, comma separated")
        parser.add_argument("-a", "--addresses", dest="addresses", required=True,
                            help="List of addresses, comma separated")
        parser.add_argument("-k", "--ssh-pub-key", dest="ssh_pub_key", required=True,
                            help="SSH public key file for the cluster")
        parser.add_argument("-K", "--ssh-priv-key", dest="ssh_priv_key", required=True,
                            help="SSH privaate key file for the cluster")
        parser.add_argument("--dry-run", dest="dry_run", required=False, default=False,
                            action="store_true", help="Run without installing CoreOS")
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (git) and the subcommand (commit)
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterInit(args)

    def route(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1], description="Route VMs IP ranges to allow inbound traffic")
        # prefixing the argument with -- means it's optional
        parser.add_argument("-r", "--remove", dest="remove", required=False,
                            action="store_true", help="Remove routes")
        parser.add_argument("-b", "--bridge", dest="bridge", required=False,
                            help="Bridge used by virtualbox (ex: br0)")
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterRoute(args)

    def nat(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1],
                                         description="NAT tcp/udp containers ports on the public static ip")
        # prefixing the argument with -- means it's optional
        parser.add_argument("-e", "--etcd_dir", dest="etcd_dir", required=False,
                            help="Etcd dir to read from")
        parser.add_argument("-b", "--bridge", dest="bridge", required=False,
                            help="Bridge used by virtualbox (ex: br0)")
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterNat(args)

    def proxy(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1], description="Proxy containers http ports using nginx")
        # prefixing the argument with -- means it's optional
        parser.add_argument("-e", "--etcd_dir", dest="etcd_dir", required=False,
                            help="Etcd dir to read from")
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterProxy(args)
