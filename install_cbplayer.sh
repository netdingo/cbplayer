#!/bin/sh
PROG_PATH=/root/cbplayer
INIT_PATH=/etc/init.d
SCRIPT=cbplayer.sh
cp -f ${PROG_PATH}/$SCRIPT ${INIT_PATH}
[ ${INIT_PATH}/$SCRIPT ] && update-rc.d $SCRIPT defaults
