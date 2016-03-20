import os
import sys
import logging
import argparse

from .config import cfg
from .shell import which
from .modules.init import CrisidevClusterInit
from .modules.install import CrisidevClusterInstall
from .modules.route import CrisidevClusterRoute
from .modules.lb import CrisidevClusterLB
from .modules.proxy import CrisidevClusterProxy
from .modules.prom import CrisidevClusterProm


class CrisidevCtl(object):

    def __init__(self):
        self.log = logging.getLogger(__name__)
        parser = argparse.ArgumentParser(
            description="Crisidev Cloud Control",
            usage="""crisidevctl <command> [<args>]

Commands:
   install          Install required files on the host machine
   init             Initialise VMs images for a new cluster
   route            Routes VMs subnet to allow inbound traffic
   lb               LB containers tcp/udp ports on the public ip address
   proxy            Proxy containers http ports using nginx
   prometheus       Setup prometheus targets for monitoring

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
        parser.add_argument("-D", "--disk_size", dest="disk_size", required=False, default=0,
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
        parser.add_argument("-d", "--domain", dest="domain", required=True,
                            help="domain name for the cluster")
        parser.add_argument("-C", "--cluster", dest="cluster", required=True,
                            help="cluster name")
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

    def lb(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1],
                                         description="LB tcp/udp containers ports on the public static ip")
        # prefixing the argument with -- means it's optional
        parser.add_argument("-c", "--cleanup", dest="cleanup", required=False,
                            action="store_true", help="Cleanup LB")
        parser.add_argument("-e", "--etcd_dir", dest="etcd_dir", required=False,
                            help="Etcd dir to read from")
        parser.add_argument("-b", "--bridge", dest="bridge", required=False,
                            help="Bridge used by virtualbox (ex: br0)")
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterLB(args)

    def proxy(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1], description="Proxy containers http ports using nginx")
        # prefixing the argument with -- means it's optional
        parser.add_argument("-e", "--etcd_dir", dest="etcd_dir", required=False,
                            help="Etcd dir to read from")
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterProxy(args)

    def prom(self):
        parser = argparse.ArgumentParser(prog=sys.argv[1], description="Setup prometheus targets for monitoring")
        # prefixing the argument with -- means it's optiona
        parser.add_argument("-e", "--etcd_dir", dest="etcd_dir", required=False,
                            help="Etcd dir to read from")
        parser.add_argument("-p", "--prom_file", dest="prom_file", required=False,
                            help="Prometheus targets file")
        args = parser.parse_args(sys.argv[2:])
        return CrisidevClusterProm(args)
