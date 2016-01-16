.PHONY=all install

all: check-env install

install: copy-files install-go-bin install-crisidevctl

copy-files:
	sudo mkdir -p /etc/crisidev
	sudo cp ./files/crisidev/* /etc/crisidev/
	cat ./files/crisidev/nginx-http.conf.tmpl |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/crisidev/nginx-http.conf.tmpl
	cat ./files/crisidev/nginx-https.conf.tmpl |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/crisidev/nginx-https.conf.tmpl
	cat ./config.json |sed 's/USERNAME/$(USERNAME)/g' |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/crisidev/config.json
	sudo cp ./bin/coreos-install /usr/local/bin
	echo "REMEMBER TO CHECK /etc/$(CLUSTER)/config.json"
	cat ./files/cluster_host/nginx/unsecure |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/nginx/sites-enabled/unsecure
	cat ./files/cluster_host/systemd/crisidevctl.service |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |sudo tee /etc/systemd/system/crisidevctl.service

install-go-bin:
	mkdir -p $(HOME)/go
	export GOPATH=$$HOME/go
	export PATH=$$GOPATH/bin:$$PATH
	go get -v github.com/coreos/etcd/etcdctl
	go get -v github.com/coreos/fleet/fleetctl
	go install -v github.com/coreos/etcd/etcdctl
	go install -v github.com/coreos/fleet/fleetctl
	sudo cp $$GOPATH/bin/etcdctl /usr/local/bin
	sudo cp $$GOPATH/bin/fleetctl /usr/local/bin

install-crisidevctl:
	sudo python setup.py install

check-env:
ifndef USERNAME
	$(error USERNAME is undefined)
endif
ifndef CLUSTER
	$(error CLUSTER is undefined)
endif
ifndef DOMAIN
	$(error DOMAIN is undefined)
endif
