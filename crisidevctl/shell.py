import os
import logging
import envoy

log = logging.getLogger(__name__)


def runcmd(cmd, alert=True):
    log.info("envoy command: \"{}\"".format(cmd))
    r = envoy.run(cmd)
    if r.std_out:
        for line in r.std_out.split("\n"):
            log.info(line.rstrip("\n\r"))
    log.info("envoy exit code: {}".format(r.status_code))
    if r.status_code != 0 and r.std_err and alert:
        log.error(r.std_err)
    return r.status_code, r.std_out, r.std_err


def which(name):
    for path in os.getenv("PATH").split(os.path.pathsep):
        if os.path.exists(os.path.join(path, name)):
            return 0
    log.error("{} not found in $PATH".format(name))
    return 1
