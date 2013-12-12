#!/usr/bin/env python

import sys, time
from daemon import Daemon
from cbplayer import do_daemon
from constants import prog_home

class CbplayerDaemon(Daemon):
    def run(self):
        do_daemon()

if __name__ == "__main__":
    logfile = prog_home + "/log.txt" 
    #daemon = CbplayerDaemon('/var/run/cbplayer-daemon.pid', stdout= logfile, stderr = logfile)
    #slow tf card should setup stdout/stderr, which will hold os seriously
    daemon = CbplayerDaemon('/var/run/cbplayer-daemon.pid') ## 
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
