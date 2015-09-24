FROM armv7/armhf-debian

MAINTAINER Bigo <bigo@crisidev.org>

RUN echo 'APT::Install-Suggests "0";' > /etc/apt/apt.conf.d/99local
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/99local
RUN echo "deb http://apt.crisidev.org jessie main" >> /etc/apt/sources.list
RUN apt-get update && apt-get -y install wget locales
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen
RUN wget -O - http://apt.crisidev.org/bigo@crisidev.org.gpg.key |apt-key add -

RUN apt-get update && apt-get -y install libfontconfig adduser openssl ca-certificates grafana

RUN mkdir -p /var/lib/grafana
ADD grafana.ini /etc/grafana/
ADD prometheus /usr/share/grafana/public/app/plugins/datasource/prometheus

WORKDIR /usr/share/grafana

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

EXPOSE 3000

ENTRYPOINT ["/usr/sbin/grafana-server", "--config", "/etc/grafana/grafana.ini"]
