FROM debian:jessie

MAINTAINER Bigo <bigo@crisidev.org>

RUN apt-get update && apt-get -y install wget localepurge locales
RUN echo "deb http://apt.crisidev.org jessie main" >> /etc/apt/sources.list
RUN wget -O - http://apt.crisidev.org/bigo@crisidev.org.gpg.key |apt-key add -
RUN echo "en_IE.UTF-8 UTF-8\nen_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen
RUN dpkg-reconfigure localepurge

# Add f***ing skype architecture
RUN dpkg --add-architecture i386
# Update and install
RUN apt-get update && apt-get -y install skype tightvncserver blackbox libwebp5 python-pip \
  xutils xbase-clients xfonts-base xfonts-75dpi xfonts-100dpi ca-certificates openssl \
  python-dbus python-gobject dbus dbus-x11

# Add skype user, create key and setup authorisation
RUN groupadd -g 500 skype
RUN useradd --home-dir /home/skype -u 500 -g 500 -m skype

# Skypeeeee
RUN mkdir -p /home/skype/.skyped
RUN mkdir -p /home/skype/.Skype/sbigol
RUN mkdir -p /home/skype/.vnc
ADD passwd /home/skype/.vnc/passwd
ADD skyped.conf /home/skype/.skyped/
ADD skyped.cnf /home/skype/.skyped/
RUN openssl req -new -x509 -days 365 -nodes -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" \
	 -config /home/skype/.skyped/skyped.cnf -out /home/skype/.skyped/skyped.cert.pem -keyout /home/skype/.skyped/skyped.key.pem
RUN wget https://github.com/awahlig/skype4py/archive/master.tar.gz -O /tmp/skype4py.tar.gz
RUN cd /tmp && tar xfvz skype4py.tar.gz && cd skype4py-master && python setup.py install
RUN wget https://raw.githubusercontent.com/vmiklos/bitlbee-skype/master/skyped.py -O /usr/bin/skyped && chmod +x /usr/bin/skyped
RUN chown -R skype:skype /home/skype

# Add entrypoint
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

EXPOSE 2727

# Start skype
CMD ["/run.sh"]
