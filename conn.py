## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard conn module, test internet connection
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time
import cbtask
import psutil
import pdb
from mplayer import exec_shell_cmd
from constants import *

class ConnTask(cbtask.CbPlayerTask):
    """
        test internet connection
    """
    def __init__(self, name):
        cbtask.CbPlayerTask.__init__(self, name)
        self.exit = False
        self.output = name
        self.attr = 0 

    def main(self): ## task entry 
        ret = 0
        ret = E_NO_ERR
        srv = "www.baidu.com"
        self.set_output("0", 3)
        exit_code = exec_shell_cmd('ping', "-c", "2", srv) 
        if exit_code != 0:
            self.set_output("0")
        else:
            self.set_output("1")
        time.sleep(3)
        self.set_output(self.get_name(), 0)
        return ret 

    def set_output(self, s, attr=0):
        self.output = s
        self.attr = attr

    def get_output(self):
        return (self.output, self.attr)

    def handle_exit_key(self): ##
        self.exit = True
        pass

if __name__ ==  "__main__" :
    pass
