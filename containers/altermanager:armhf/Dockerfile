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
RUN wget http://repo.crisidev.org/armhf/alertmanager -O /usr/local/bin/alertmanager
RUN chmod +x /usr/local/bin/alertmanager
RUN mkdir -p /etc/altermanager

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

CMD ["/usr/local/bin/alertmanager", \
     "-config.file", "/etc/altermanager/altermanager.conf", \
     "-notification.smtp.smarthost", "172.17.42.1"]
