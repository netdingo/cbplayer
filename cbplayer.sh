#!/bin/sh
### BEGIN INIT INFO
# Provides:          cbplayer.sh
# Required-Start:    $local_fs $remote_fs $syslog
# Required-Stop:     $local_fs $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: starts cbplayer daemon
# Description:       starts cbplayer daemon with python
### END INIT INFO

PROG_PATH=/root/cbplayer
do_start()
{
    cd ${PROG_PATH}
    python ./cbplayer-daemon.py start
}
do_stop()
{
    cd ${PROG_PATH}
    python ./cbplayer-daemon.py stop
}

case "$1" in
start)
do_start
;;
stop)
do_stop
;;
*)
echo "useage:snsserver {start|stop}"
exit 1
;;
esac

exit 0
