#!/bin/bash
su bigo -c "deluged -c /crisidev-share/snatch/deluge -l /var/log/deluged/daemon.log -L info"
su bigo -c "deluge-web -c /crisidev-share/snatch/deluge -l /var/log/deluged/web.log -L info &"
tail -f /var/log/deluged/daemon.log /var/log/deluged/web.log
