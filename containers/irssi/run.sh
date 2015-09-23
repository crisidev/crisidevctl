#!/bin/sh

if [ ! -e /home/irssi/.ssh/authorized_keys ]; then
  if [ -n "${SSH_PUB_KEY}" ]; then
    echo "Pub key to access irssi:"
    echo "${SSH_PUB_KEY}"
    mkdir -p /home/irssi/.ssh
    echo "${SSH_PUB_KEY}" > /home/irssi/.ssh/authorized_keys
    chown -R irssi:irssi /home/irssi/.ssh
  fi
fi

echo "Executing $*"
exec $*
