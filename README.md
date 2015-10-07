# crisidev-cloud
## scripts for my dev cloud

## Quirks
* User bigo on host must have the same UID of user core on guests (500)
* Group bigo on host must have the same GUID of group core on guests (500)

## Notes
### Setup hugepages
vm.nr_hugepages = 5800
Reboot

### Create /crisidev-share
### /dev/md1 create /dev/crisidev vg

### Install vm
virt-install --network bridge=br0,model=virtio --name=node1.crisidev.org --disk path=/dev/crisidev/node1,bus=virtio,io=native --ram 2560 --vcpus=2 --check-cpu --hvm --nographics --memballoon model=virtio --memorybacking hugepages=on --filesystem /crisidev-share,crisidev-share --filesystem /unsafe,unsafe --boot hd
