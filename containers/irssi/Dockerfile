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

# Update and install
RUN apt-get update && apt-get -y install tmux irssi irssi-plugin-otr ssh vim-nox \
  tmux ca-certificates libtime-duration-perl libtimedate-perl

RUN mkdir /var/run/sshd

# Add irssi user, create key and setup authorisation
RUN groupadd -g 500 irssi
RUN useradd --shell /bin/bash --home-dir /home/irssi -u 500 -g 500 -m irssi
ADD irssi /home/irssi/irssi
ADD tmux.conf /home/irssi/.tmux.conf
RUN chmod +x /home/irssi/irssi
RUN chown -R irssi:irssi /home/irssi

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
EXPOSE 22

# Start ssh
CMD ["/run.sh", "/usr/sbin/sshd", "-D"]
