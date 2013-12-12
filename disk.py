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
import pdb

class IPTask(cbtask.CbPlayerTask):
    """
        do IP playing
    """
    def __init__(self, name):
        cbtask.CbPlayerTask.__init__(self, name)

    def main(self): ## task entry 
        ret = 0
        return ret 
        pass

    def handle_enter_key(self): ##
        #TODO
        pass

    def handle_exit_key(self): ##
        #TODO
        pass

    def handle_left_key(self): ##
        #TODO
        pass

    def handle_right_key(self): ## 
        #TODO
        pass

if __name__ ==  "__main__" :
    pass
