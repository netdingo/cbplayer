## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard constant module, common-used global variable.
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time
import pdb
from   led import LED_COUNT 
import platform

RUNNING_MODE_DEBUG  = 0 ## debug
RUNNING_MODE_NORMAL = 1 ## running

RUNNING_MODE = RUNNING_MODE_NORMAL

ir_fifo = "/var/ir_fifo"

KEY_MAX_INTERVAL = 4
nas_srv   = "192.168.0.111"
media_dir = "/mnt/sda3/media/songs"
#media_dir = "/mnt/sda3/media/testsongs"
local_dir = "/mnt/songs"


isLinux = platform.system() != 'Windows'  

if isLinux:
    prog_home = '/root/cbplayer'
else:
    prog_home = 'C:\\'

REMOTE_CONF_FILE = os.path.join(prog_home, "lg_remote.conf")
LOG_FILE = os.path.join(prog_home, "log.txt")
RADIO_CONF = os.path.join(prog_home, "radio_list.ini")

DEFAULT_LED_DURATION = 3
CUBIEBOARD_IR_DRV = "sun4i-ir"
CUBIEBOARD_MIXER_DRV = "snd_mixer_oss"

E_NO_ERR      = 0
E_NO_SONG_DIR = 1
E_FAIL_CONN_MEDIA_SRV = 2
E_NO_MEDIA_EXPORT = 3
E_FAIL_MOUNT_MEDIA_SRV = 4
E_TOO_LARGE_STRING = 5
E_FAIL_CREATE_DIR  = 6
E_FAIL_LOAD_MIXER_DRIVER = 7

if __name__ ==  "__main__" :
    pass
