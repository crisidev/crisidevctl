FROM debian:jessie

MAINTAINER Bigo <bigo@crisidev.org>

RUN echo 'APT::Install-Suggests "0";' > /etc/apt/apt.conf.d/99local
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/99local
RUN apt-get update && apt-get -y install wget localepurge locales
RUN echo "deb http://shell.ninthgate.se/packages/debian wheezy main" >> /etc/apt/sources.list
RUN wget -O - http://shell.ninthgate.se/packages/shell-ninthgate-se-keyring.key |apt-key add -
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen
RUN dpkg-reconfigure localepurge

# Update and install
RUN apt-get update && apt-get -y install plexmediaserver

# Add irssi user, create key and setup authorisation
RUN groupadd -g 500 bigo
RUN useradd --shell /bin/bash --home-dir /home/bigo -u 500 -g 500 -m bigo

# Plex
RUN chown -R bigo:bigo /var/lib/plexmediaserver
ADD start_pms /usr/sbin/start_pms
RUN chmod +x /usr/sbin/start_pms

ADD run.sh /run.sh
RUN chmod +x /run.sh

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

# SSH port
EXPOSE 32400

# Start ssh
CMD ["/run.sh"]
