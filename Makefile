.PHONY=all install

all: install

install: copy-files

copy-files:
	sudo mkdir -p /$(CLUSTER)
	sudo cp ./files/crisidev/* /etc/$(CLUSTER)
	sudo cp ./config.json /etc/$(CLUSTER)
	sudo cp ./bin/coreos-install /usr/local/bin
	echo "REMEMBER TO EDIT /etc/$(CLUSTER)/config.json"
	cat ./files/cluster_host/nginx/unsecure |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/nginx/sites-enabled/unsecure
	cat ./files/cluster_host/systemd/crisidevctl.service |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/systemd/system/crisidevctl.service

install-go-bin:
	mkdir -p $(HOME)/go
	echo "export GOPATH=$HOME/go" | tee $(HOME)/.bashrc
	echo "export PATH=$GOPATH:$PATH" | tee -a $(HOME)/.bashrc
	source $(HOME)/.bashrc
	go get -v github.com/coreos/etcd
	go get -v github.com/coreos/fleet
	go install -v github.com/coreos/etcd
	go install -v github.com/coreos/fleet

install-crisidevctl:
	sudo python setup.py install
