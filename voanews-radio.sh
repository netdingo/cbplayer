#!/bin/bash
#
# http://www.voanews.com/wm/live/newsnow.asx
#
#

urlVOA=http://www.voanews.com/wm/live/newsnow.asx
baidu=baidu.com
ping -c 1 baidu.com > /dev/null 2>&1
exit_code=$?
[ $exit_code = 0 ] || exit 0

# Get file from $urlVOA
fileASX=$(basename $urlVOA)
wget -q $urlVOA

# Get file from the URL in $fileASX
wget -q -i $fileASX

# Get real ASX
realASX=$(basename `cat $fileASX`)

# Parsing $URL
URL=`sed -n '/REF/p' $realASX | awk -F "[\"\"]" '{print $2}' `
URL=`echo $URL | awk '{print $1}'`

# Remove tmp files
rm $fileASX $realASX

[ x$1 = x"play" ] &&  mplayer $URL
[ x$1 = x"" ] && echo $URL
exit 0
