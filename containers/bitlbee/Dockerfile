FROM debian:jessie

MAINTAINER Bigo <bigo@crisidev.org>

RUN echo 'APT::Install-Suggests "0";' > /etc/apt/apt.conf.d/99local
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/99local
RUN apt-get update && apt-get -y install wget localepurge locales
RUN echo "deb http://apt.crisidev.org jessie main" >> /etc/apt/sources.list
RUN wget -O - http://apt.crisidev.org/bigo@crisidev.org.gpg.key |apt-key add -
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen
RUN dpkg-reconfigure localepurge

# bitlbee user
RUN groupadd -g 500 bitlbee
RUN adduser --system --home /var/lib/bitlbee --shell /bin/sh bitlbee -uid 500 -gid 500

# Update and install
RUN apt-get update && apt-get -y install bitlbee-facebook bitlbee-libpurple \
	pidgin-whatsapp telegram telegram-cli locales ca-certificates

# Locales
RUN dpkg-reconfigure locales
RUN locale-gen en_US.UTF-8

# Add bitlbee config
ADD bitlbee.conf /etc/bitlbee/bitlbee.conf

# Skypeeeee
ADD skype.so /usr/lib/bitlbee/

# init
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
EXPOSE 6667

# Start bitlbee
CMD ["/run.sh"]
