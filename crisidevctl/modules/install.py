import logging

log = logging.getLogger(__name__)

# mkdir -p /etc/crisidev
# ln -s templates/firewall.safe /etc/crisidev
# ln -s templates/firewall /etc/crisidev/firewall.tmpl
# ln -s templates/nginx-http.conf  /etc/crisidev/nginx-http.conf.tmpl
# ln -s templates/nginx-https.conf  /etc/crisidev/nginx-https.conf.tmpl


class CrisidevClusterInstall(object):
    def __init__(self):
        pass

    def __call__(self):
        raise NotImplementedError
