.PHONY=all install

all: check-env install

install: copy-files install-crisidevctl

copy-files:
	mkdir -p /etc/crisidev
	cp ./files/crisidev/* /etc/crisidev/
	cat ./files/crisidev/nginx-http.conf.tmpl |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |tee /etc/crisidev/nginx-http.conf.tmpl
	cat ./files/crisidev/nginx-https.conf.tmpl |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |tee /etc/crisidev/nginx-https.conf.tmpl
	cat ./config.json |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |tee /etc/crisidev/config.json
	cp ./bin/coreos-install /usr/local/bin
	echo "REMEMBER TO CHECK /etc/$(CLUSTER)/config.json"
	cat ./files/cluster_host/nginx/secure |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |tee /etc/nginx/sites-enabled/secure
	cat ./files/cluster_host/nginx/unsecure |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |tee /etc/nginx/sites-enabled/unsecure
	cat ./files/cluster_host/systemd/crisidevctl.service |sed 's/DOMAIN/$(DOMAIN)/g' |sed 's/CLUSTER/$(CLUSTER)/g' |tee /etc/systemd/system/crisidevctl.service

install-fleet:
	wget https://github.com/coreos/fleet/releases/download/v0.11.5/fleet-v0.11.5-linux-amd64.tar.gz -O /tmp/fleet.tar.gz
	tar xfvz -C /tmp/fleet fleet.tar.gz
	mv fleet/fleet* /usr/local/bin
	rm -rf /tmp/fleet*

install-etcd:
	wget ttps://github.com/coreos/etcd/releases/download/v2.2.3/etcd-v2.2.3-linux-amd64.tar.gz -O /tmp/etcd.tar.gz
	tar xfvz -C /tmp/etcd etcd.tar.gz
	mv etcd/etcd* /usr/local/bin
	rm -rf /tmp/etcd*


install-go-bin:
	mkdir -p $(HOME)/go
	export GOPATH=$$HOME/go
	export PATH=$$GOPATH/bin:$$PATH
	go get -v github.com/coreos/etcd/etcdctl
	go get -v github.com/coreos/fleet/fleetctl
	go install -v github.com/coreos/etcd/etcdctl
	go install -v github.com/coreos/fleet/fleetctl
	cp $$GOPATH/bin/etcdctl /usr/local/bin
	cp $$GOPATH/bin/fleetctl /usr/local/bin

install-crisidevctl:
	python setup.py install

check-env:
ifndef CLUSTER
	$(error CLUSTER is undefined)
endif
ifndef DOMAIN
	$(error DOMAIN is undefined)
endif
