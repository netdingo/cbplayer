#!/bin/sh
/usr/bin/mplayer -slave -nolirc -quiet -input file=/var/mplayer_input $1 2>/dev/null
