#!/bin/bash
/usr/sbin/bitlbee -c /etc/bitlbee/bitlbee.conf
tail -F -n 100 /etc/bitlbee/motd.txt
