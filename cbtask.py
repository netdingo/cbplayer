## encoding=utf-8
#!/usr/bin/env python
"""
  task module, which handles the specific task 
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time, threading, Queue
from log import cblog
import pdb

TASK_STOP    = 0   ## thread does not start yet
TASK_RUNNING = 1   ## thread is running
TASK_END     = 2   ## thread has endded

class CbPlayerTask(threading.Thread):
    task_list    = []
    main_task    = None
    current_task = None
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name 
        self.order = None
        self.status = TASK_STOP
        self.exit_thread = False
        pass

    def run(self):
        self.status = TASK_RUNNING 
        while not self.exit_thread:
            exit_code = self.call_method('main')        
            if exit_code <= 0:
                break
        self.status = TASK_END

    def call_callback(self):
        return self.call_method('_callback')

    def call_method(self, method):        
        main_method = getattr(self, method) if hasattr(self, method) else None
        exit_code   = main_method() if main_method else -1
        return exit_code

    def get_current_task(self):
        return CbPlayerTask.current_task

    def get_task(self, task = None, dir=1):
        if task == None:
           task = self.get_current_task()
        if task not in CbPlayerTask.task_list:
            return None
        idx = CbPlayerTask.task_list.index(task)
        count = len(CbPlayerTask.task_list)
        idx = (idx + dir ) % count
        return CbPlayerTask.task_list[idx]

    def get_prev_task(self, task = None):
        return self.get_task(task, -1)

    def get_next_task(self, task = None):
        return self.get_task(task, 1)

    def set_current(self, task = None):    
        if task == None:
            task = self
        CbPlayerTask.current_task = task

    def get_status(self):
        return self.status 

    def is_running(self):        
        ret = (self.get_status() == TASK_RUNNING)
        return ret

    def is_stopped(self):        
        ret = (self.get_status() == TASK_STOP)
        return ret

    def is_end(self):        
        ret = (self.get_status() == TASK_END)
        return ret

    def get_output(self):
        """
           need to be override by each task
           should return the following tuple:
           ( msg, blink )
        """
        assert(0)

    def get_name(self):
        return self.name

    def register(self, order):
        self.order = order
        if self.name == "main":
            CbPlayerTask.main_task = self
        else:
            CbPlayerTask.task_list.append(self)

    def recreate_task(self, task):
        if task == None:
            return False
        if task not in CbPlayerTask.task_list:
            return None
        idx = CbPlayerTask.task_list.index(task)
        cls = task.__class__
        new_task = cls(task.name) 
        new_task.name  = task.name
        new_task.order = task.order
        new_task.status= TASK_STOP
        if CbPlayerTask.current_task == task:
            CbPlayerTask.current_task = new_task
        CbPlayerTask.task_list[idx] = new_task
        del task
        return new_task

    def log(self, msg):
        print msg
        cblog(msg)

if __name__ ==  "__main__" :
    pass 
