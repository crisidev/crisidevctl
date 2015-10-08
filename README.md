# crisidev-cloud - scripts for my dev cloud
A set of python / bash / golang tools to setup my own cloud.
This is based on Debian, KVM, CoreOS, Docker and a huge list of other opensource software.

**DISCLAIMER: USE AT YOUR OWN RISK, THIS IS MY PERSONAL SETUP, JUST MADE A LITTLE BIT GENERAL TO ALLOW PEOPLE TO PLAY WITH IT. IT IS PROBABLE YOU WILL HAVE TO DIG IN CODE / CONFIGS IF YOU USE THIS :)**

## Table of contents
* [crisidev-cloud - scripts for my dev cloud](#crisidev-cloud---scripts-for-my-dev-cloud)
  * [DNS wildcard, cluster name and username](#dns-wildcard,-cluster-name-and-username)
    * [Create source file](#create-source-file)
  * [Install bare-metal host](#install-bare-metal-host)
    * [The partition layer should follow this:](#the-partition-layer-should-follow-this:)
    * [Prepare LVM and partitions](#prepare-lvm-and-partitions)
    * [Setup permissions](#setup-permissions)
    * [Setup hugepages](#setup-hugepages)
    * [Install base system](#install-base-system)
    * [Setup networking](#setup-networking)
    * [Configure Hypervisor](#configure-hypervisor)
    * [Setup nginx](#setup-nginx)
  * [Install crisidevctl](#install-crisidevctl)
  * [Install CoreOS VMs](#install-coreos-vms)
    * [Configure VM disks](#configure-vm-disks)
    * [Setup VMs](#setup-vms)
  * [Start CoreOS VMs](#start-coreos-vms)
    * [Check cluster status](#check-cluster-status)
    * [Manual iptables / nginx / route update](#manual-iptables-/-nginx-/-route-update)

### DNS wildcard, cluster name and username
Point a DNS wildcard on you nameserver. The TLD will be your cluster name.
* **DOMAIN:** blackmesalabs.it
* **CLUSTER:** blackmesalabs
* **USENAME:** core 

#### Create source file
Create a file to source from with env variables
```sh
export DOMAIN=blackmesalabs.it
export CLUSTER=blackmesalabs
export USERNAME=core
```

### Install bare-metal host
Install debian-jessie on a bare-metal host with enough juice to run Virtual Machines.
#### The partition layer should follow this:
* **/** On RAID 1 ~60Gb
* Around 200Gb allocated into and LVM VG named $CLUSTER
* **/$CLUSTER-share** On RAID 1, the remaining space 

Example for Etzner (you'll need to create the LVM by hand):
```sh
PART swap swap 6G
PART / ext4 64G
PART /removeme ext4 250G
PART /$CLUSTER-share ext4 all
```

#### Prepare LVM and partitions
Let's make the partions what they shoud be
```sh
$ export DOMAIN=blackmesalabs.it
$ export CLUSTER=blackmesalabs
$ umount /removeme && rmdir /removeme
$ pvcreate /dev/md2 && pvdisplay
$ vgcreate $CLUSTER /dev/md2 && vgdisplay
```
Remove /removeme from /etc/fstab

#### Setup permissions
Running user and group on host must have the same UID and GID of user core user on guests (500)
```sh
$ export USERNAME=core
$ groupadd -g 500 $USERNAME
$ useradd --shell /bin/bash --home-dir /$CLUSTER-share -u 500 -g 500 -m $USERNAME
$ passwd $USERNAME
$ cp ~/.bashrc /$CLUSTER-share/.bash_profile
$ chown -R $USERNAME:$USERNAME /$CLUSTER-share
```
#### Setup hugepages
Export to sysctl how many hugepages you want to use for KVM. Calculation is max memory usable by VMs in Mb / 2
```sh
vm.nr_hugepages = 5800
vm.hugetlb_shm_group = 500
```
**Reboot** to reserve that memory (see hugetlb)

#### Install base system
** SOURCE AGAIN THE VARIABLES **
```sh
$ echo "deb http://http.debian.net/debian jessie-backports main contrib non-free" |tee -a /etc/apt/sources.list
$ apt-get update && apt-get -y upgrade && apt-get -y install locales htop iotop bmon dstat vim-nox bridge-utils sudo python-dev python-pip nginx git bash-completion whois && dpkg-reconfigure locales
$ echo "deb http://http.debian.net/debian experimental main contrib non-free" |tee -a /etc/apt/sources.list
$ apt-get update && apt-get install golang -t experimental
```

#### Setup networking
Add a bridge for VMs to /etc/network/interfaces
```sh
auto br0
iface br0 inet static
  pre-up modprobe tun
  bridge_ports none
  bridge_fd 0
  address 192.168.0.1
  broadcast 192.168.0.255
  netmask 255.255.255.0
  
$ ifup br0
```
Setup /etc/resolv.conf
```sh
domain $DOMAIN
search $DOMAIN
nameserver 192.168.0.2
nameserver 8.8.8.8
```
#### Configure Hypervisor
```sh
$ apt-get install -y qemu-kvm libvirt-bin virtinst kpartx
$ systemctl stop libvirtd.service
$ systemctl stop libvirt-guests.service
```

Change hugetlb in /etc/libvirt/qemu.conf
```sh
hugetlbfs_mount = "/dev/hugepages"
```

Add $USERNAME to libvirt groups
```sh
$ adduser $USERNAME $USERNAME
$ adduser $USERNAME sudo
```
Restart libvirt
```sh
$ systemctl start libvirtd.service
```

#### Setup nginx
Clean nginx installation and edit /etc/nginx/nginx.conf to have workers running as $USERNAME
```sh
$ systemctl stop nginx.service
$ rm -rf /etc/nginx/sites-enabled/*
```

Create SSL certs and htpasswd
```sh
$ mkdir -p /etc/nginx/ssl
$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt
$ printf "USER:$(openssl passwd -crypt PASSWORD)\n" >> /etc/nginx/ssl/htpasswd # (replace USER and PASSWORD)
```

Restart nginx
```sh
$ systemctl start nginx.service
```

### Install crisidevctl
```sh
$ su $USERNAME
$ export USERNAME=core; export DOMAIN=blackmesalabs.it; export CLUSTER=blackmesalabs
$ cd && git clone git://git.crisidev.org/crisidevctl && cd crisidevctl
$ export GOPATH=$HOME/go 
$ export PATH=$GOPATH/bin:$PATH
$ make # (this will install everythind run some commands as sudo)
```

### Install CoreOS VMs
#### Configure VM disks
```sh
$ ssh-keygen
$ sudo crisidevctl init -k $HOME/.ssh/id_rsa.pub -K $HOME/.ssh/id_rsa -c /etc/crisidev/crisidev.yml.tmpl -n node0.$DOMAIN,node1.$DOMAIN,node2.$DOMAIN -a 192.168.0.2,192.168.0.3,192.168.0.4 -e -D 64 -d $DOMAIN -C $CLUSTER
``` 

#### Setup VMs
```sh
$ for x in node0 node1 node2; do
    sudo virt-install --network bridge=br0,model=virtio --name=$x.$DOMAIN --disk \
    path=/dev/$CLUSTER/$x,bus=virtio,io=native --ram 3072 --vcpus=4  --check-cpu \
    --hvm --nographics --memballoon model=virtio --memorybacking hugepages=on \
    --filesystem /$CLUSTER-share,$CLUSTER-share --boot hd --noreboot
  done
```

### Start CoreOS VMs
```sh
$ sudo /etc/crisidev/firewall.safe
$ for x in 0 1 2; do sudo virsh start node$x.$DOMAIN; done
$ sudo virsh list
$ virsh console node0.$DOMAIN
```
#### Check cluster status
If everything went fine we should be able to ping our new VMs
```sh
$ for x in 2 3 4; do ping -c2 -w1 192.168.0.$x; done
```
Etcd2 should be up in a couple of minutes, and some other time is needed for DNS server and VMs layer 3 connectivity. Wait a bit and than check Etcd2
```sh
$ curl $(cat /etc/crisidev/etcd.key)
$ dig @192.168.0.2 etcd.$DOMAIN
$ etcdctl -C http://etcd.$DOMAIN:4001 ls --recursive
$ ssh-add 
$ ssh core@node0
```

#### Manual iptables / nginx / route update
If everything is setup we should be able to update routing, the firewall and nginx and see if fleetui is up and running
```sh
$ sudo crisidevctl route
$ sudo crisidevctl nat
$ sudo crisidevctl proxy
```
Go to https://fleeui.$DOMAIN
