# crisidev-cloud - scripts for my dev cloud
## Installation
### DNS wildcard, cluster name and username
Point a DNS wildcard on you nameserver. The TLD will be your cluster
name.
* **DOMAIN:** blackmesalabs.it
* **CLUSTER:** blackmesalabs
* **USENAME:** core 

### Install bare-metal host
Install debian-jessie on a bare-metal host with enough juice to run
Virtual Machines.
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
Running user and group on host must have the same UID and GID of user
core user on guests (500)
```sh
$ export USERNAME=core
$ groupadd -g 500 $USERNAME
$ useradd --shell /bin/bash --home-dir /$CLUSTER-share -u 500 -g 500 -m
$USERNAME
$ passwd $USERNAME
$ chown -R $USERNAME:$USERNAME /$CLUSTER-share
```
#### Setup hugepages
Export to sysctl how many hugepages you want to use for KVM. Calculation
is max memory usable by VMs in Mb / 2
```sh
vm.nr_hugepages = 5800
```
**Reboot** to reserve that memory (see hugetlb)

#### Install base system
** SOURCE AGAIN THE VARIABLES **
```sh
$ apt-get update && apt-get -y upgrade && \ 
    apt-get -y install locales htop iotop bmon dstat vim-nox
bridge-utils && \
    dpkg-reconfigure locales sudo python-dev python-pip qemu-kvm
libvirt-bin && \
    nginx git bash-completion kpartx whois virtinst && adduser $USERNAME
sudo && \
    adduser $USERNAME kvm && adduser $USERNAME libvirt
$ echo "deb http://http.debian.net/debian experimental main contrib
non-free" |tee -a /etc/apt/sources.list
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
#nameserver 192.168.0.2
nameserver 8.8.8.8
```
#### Configure Hypervisor
```sh
$ apt-get install -y qemu-kvm libvirt-bin nginx git bash-completion
$ systemctl stop libvirtd.service
$ chown -R $USERNAME:$USERNAME /var/lib/libvirt/qemu
```

Change running user to $USERNAME in /etc/libvirt/qemu.conf
```sh
...
#       user = "100"    # A user named "100" or a user with uid=100
user = "core"

# The group for QEMU processes run by the system instance. It can be
# specified in a similar way to user.
...
```

Restart libvirt
```sh
$ systemctl start libvirtd.service
```

#### Setup nginx
Clean nginx installation and edit /etc/nginx/nginx.conf to have workers
running as $USERNAME
```sh
$ systemctl stop nginx.service
$ rm -rf /etc/nginx/sites-enabled/*
```

Create SSL certs and htpasswd
```sh
$ mkdir -p /etc/nginx/ssl
$ openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout
/etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt
$ printf "USER:$(openssl passwd -crypt PASSWORD)\n" >>
/etc/nginx/ssl/htpasswd # (replace USER and PASSWORD)
```

Restart nginx
```sh
$ systemctl start nginx.service
```

### Install crisidevctl
```sh
$ su $USERNAME
$ export USERNAME=core; export DOMAIN=blackmesalabs.it; export
CLUSTER=blackmesalabs
$ cd && git clone git://git.crisidev.org/crisidevctl && cd crisidevct
$ make # (this will install everythind run some commands as sudo)

### Install CoreOS VMs
#### Configure VM disks
```sh
$ ssh-keygen
$ sudo crisidevctl init -k $HOME/.ssh/id_rsa.pub -K $HOME/.ssh/id_rsa -c
/etc/crisidev/crisidev.yml.tmpl -n
node0.$DOMAIN,node1.$DOMAIN,node2.$DOMAIN -a
192.168.0.2,192.168.0.3,192.168.0.4 -e -D 64 -d $DOMAIN -C $CLUSTER
```

#### Setup VMs
```sh
$ for x in node0 node1 node2; do
    sudo virt-install --network bridge=br0,model=virtio
--name=$x.$DOMAIN --disk path=/dev/$CLUSTER/$x,bus=virtio,io=native
--ram 3072 --vcpus=4  --check-cpu --hvm --nographics --memballoon
model=virtio --memorybacking hugepages=on --filesystem
/$CLUSTER-share,$CLUSTER-share --boot hd --noreboot
done
$ virsh -c qemu:///system list
```


