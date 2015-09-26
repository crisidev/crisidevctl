FROM armhfbuild/alpine:3.1

MAINTAINER Bigo <bigo@crisidev.org>

RUN apk add --update -t ca-certificates wget
RUN wget http://private-repo.crisidev.org/hubble/etcd -O /usr/local/bin/etcd
RUN wget http://private-repo.crisidev.org/hubble/etcdctl -O /usr/local/bin/etcdctl
RUN chmod +x /usr/local/bin/etcd /usr/local/bin/etcdctl

EXPOSE 4001 7001 2379 2380
