FROM armv7/armhf-debian

MAINTAINER Bigo <bigo@crisidev.org>

RUN echo 'APT::Install-Suggests "0";' > /etc/apt/apt.conf.d/99local
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/99local
RUN apt-get update && apt-get -y install wget locales
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen

RUN apt-get -y install ca-certificates

# Go
WORKDIR /
RUN wget http://repo.crisidev.org/armhf/prometheus -O /usr/local/bin/prometheus 
RUN wget http://repo.crisidev.org/armhf/promtool -O /usr/local/bin/promtool 
RUN chmod +x /usr/local/bin/prometheus /usr/local/bin/promtool
RUN mkdir -p /etc/prometheus /var/lib/prometheus
ADD prometheus.yml /etc/prometheus/prometheus.yml
ADD consoles /etc/prometheus/consoles
ADD console_libraries /etc/prometheus/console_libraries

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

EXPOSE 9090

CMD ["/usr/local/bin/prometheus",
     "-config.file", "/etc/prometheus/prometheus.yml",
     "-web.console.libraries", "/etc/prometheus/console_libraries",
     "-web.console.templates", "/etc/prometheus/consoles",
     "-storage.local.path", "/var/lib/prometheus"]
