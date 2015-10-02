FROM debian:jessie

MAINTAINER Bigo <bigo@crisidev.org>

RUN echo 'APT::Install-Suggests "0";' > /etc/apt/apt.conf.d/99local
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/99local
RUN apt-get update && apt-get -y install wget locales ca-certificates git openssh-client
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen

RUN mkdir -p /opus
ADD opus /opus/opus
RUN chmod +x /opus/opus

WORKDIR /usr/local/bin
RUN wget https://github.com/coreos/fleet/releases/download/v0.11.5/fleet-v0.11.5-linux-amd64.tar.gz
RUN tar xfvz fleet-v0.11.5-linux-amd64.tar.gz
RUN mv fleet-v0.11.5-linux-amd64/fleetctl /usr/local/bin
RUN rm -rf fleet-v0.11.5-linux-amd64.tar.gz
RUN chmod +x /usr/local/bin/fleetctl

WORKDIR /opus

# cleanup
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean -y && \
    apt-get autoclean -y && \
    apt-get autoremove -y && \
    rm -rf /usr/share/locale/* && \
    rm -rf /var/cache/debconf/*-old && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /usr/share/doc/*

# Start ssh
CMD ["/opus/opus"]
