#!/bin/sh
pid=`ps a -o pid=,cmd= |grep python |grep -v grep|awk '{print $1}'`
kill -9 $pid
