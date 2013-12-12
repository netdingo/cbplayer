## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard log module
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time
from  constants import LOG_FILE
import pdb

# -*- coding: utf-8 -*-
import logging
import math

logger_initd = [ False ]

logger = None
if not logger_initd[0] : 
    logger = logging.getLogger()
    #set loghandler
    file = logging.FileHandler(LOG_FILE)
    logger.addHandler(file)
    #set formater
    #formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file.setFormatter(formatter) 
    #set log level
    logger.setLevel(logging.NOTSET)
    logger_initd[0] = True

"""
for i in range(0,10):
	logger.info(str(i))
"""    

def cblog(msg, show = 0):
    global logger
    if show != 0: print msg
    logger.info(msg)
    print msg
    pass

if __name__ ==  "__main__" :
    pass
