## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard ip module, which show ip
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

class CPUTask(cbtask.CbPlayerTask):
    """
        show cpu usage 
    """
    def __init__(self, name):
        cbtask.CbPlayerTask.__init__(self, name)
        self.output = name
        self.exit = False

    def main(self): ## task entry 
        ret = 0
        while not self.exit:
            cpu = str(psutil.cpu_percent())
            self.set_output(cpu)
            time.sleep(1)
        self.set_output(self.get_name())
        return ret 
        pass

    def set_output(self, s):
        self.output = s

    def get_output(self):
        return (self.output, 0)

    def handle_exit_key(self): ##
        self.exit = True
        pass

if __name__ ==  "__main__" :
    pass
