FROM debian:jessie

MAINTAINER Bigo <bigo@crisidev.org>

RUN echo 'APT::Install-Suggests "0";' > /etc/apt/apt.conf.d/99local
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/99local
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
RUN echo 'deb http://download.mono-project.com/repo/debian beta main' | tee /etc/apt/sources.list.d/mono-xamarin-beta.list
RUN apt-get update && apt-get -y install wget locales
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen

# Update and install
RUN apt-get update && apt-get -y install ca-certificates mono-complete libmediainfo0

# Add irssi user, create key and setup authorisation
RUN groupadd -g 500 bigo
RUN useradd --shell /bin/bash --home-dir /home/bigo -u 500 -g 500 -m bigo

RUN chown -R bigo:bigo /opt/NzbDrone \
  ; mkdir -p /volumes/config/sonarr /volumes/completed /volumes/media \
  && chown -R bigo:bigo /volumes

ADD run.sh /run.sh
ADD sonarr-update.sh /sonarr-update.sh
RUN chmod +x /run.sh /sonarr-update.sh

WORKDIR /opt/
RUN wget http://update.sonarr.tv/v2/master/mono/NzbDrone.master.tar.gz
RUN tar xfvz NzbDrone.master.tar.gz
RUN rm NzbDrone.master.tar.gz

WORKDIR /opt/NzbDrone

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
EXPOSE 8989

# Start ssh
CMD ["/run.sh"]
