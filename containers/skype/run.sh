#!/bin/bash
rm -rf /tmp/.X*
su skype -c vncserver
sleep 5
export DISPLAY=:1
su skype -c "skype &"
sleep 30
su skype -c "skyped --log /tmp/skyped.log --port 2727"
tail -f /tmp/skyped.log
