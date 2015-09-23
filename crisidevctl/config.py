import json

CONFIGFILE = "/etc/crisidev/config.json"


class CrisidevCfg(object):
    def __init__(self):
        with open(CONFIGFILE) as fd:
            cfg = json.load(fd)
        for key, value in cfg.iteritems():
            try:
                getattr(self, key)
            except AttributeError:
                setattr(self, key, value)

cfg = CrisidevCfg()
