## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard player controller module, which operates cubieboard by IR remote. 
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time, Queue, stat, select
import os.path
import led, ir, log
import cbtask, mplayer, ip, cpu, conn, netradio
import constants
from constants import REMOTE_CONF_FILE
from constants import RUNNING_MODE
import pdb
 
class MainTask(cbtask.CbPlayerTask):
    """
        main task do key code dispatching, default key handling, switch task...
    """
    def __init__(self, name, ir_obj, led_obj):
        cbtask.CbPlayerTask.__init__(self, name)
        self.key_q = Queue.Queue()
        self.ir_obj = ir_obj
        self.led_obj = led_obj
        self.key_dict = ir_obj.get_key_dict()

    def main(self): ## task entry 
        while True:
            key = self.key_q.get() 
            self.handle_key(key)
        return 1
        pass

    def put_key(self, key):
        self.key_q.put(key)

    def _find_key_handler(self, task, name): 
        return getattr(task, name) if hasattr(task, name) else None

    def _exec_task_handler(self, task, key_handler_name, key):
        handler = self._find_key_handler(task, key_handler_name)
        if handler: 
            if key_handler_name == 'handle_digital_key':
                handler(key)
            else:
                handler()

    def handle_key(self, key):
        if not key: return
        key_code, key_status = key
        if key_code in self.key_dict:
            key_name = self.key_dict[key_code].lower().strip()
            key = key_name
            log.cblog("<- key %s pressed. ->" % key_name)
            if key_name in ir.digital_key:
                key_name = 'digital'
            key_handler_name = "handle_" + key_name + "_key"  
            ## find handler in current task, if not found, search it in main task
            for task in [self.get_current_task(), self]:
                self._exec_task_handler(task, key_handler_name, key)
            handler = self._find_key_handler(self, "key_event")
            if handler:
               handler(key)

    def handle_power_key(self): ## power key handler       
        import sh
        try:
            sh.poweroff()
        except Exception, e:
            print e
            pass
        #sys.exit(0)
        pass

    def handle_up_key(self): ## up key handler       
        task = self.get_prev_task()
        self.set_current(task)
        task_name = task.get_name()
        ##self.led_obj.led_output(name, 0)
        #self.led_obj.led_output(task.order)

    def handle_down_key(self): ## down key handler       
        task = self.get_next_task()
        self.set_current(task)
        task_name = task.get_name()
        ##self.led_obj.led_output(name, 0, 800)
        #self.led_obj.led_output(task.order)

    def handle_enter_key(self): ##
        task = self.get_current_task()         
        if not task: return
        if task.is_end():
            task = self.recreate_task(task) 
            if task == None:
                print "Fail to recreate new task!!"
                return 
        elif task.is_stopped():
            if not task.isAlive(): task.start()

    def refresh_led(self):
        task = self.get_current_task()         
        if task:
            if task.is_running():
                output = task.get_output()
                self.led_obj.led_output(*output)
            else:
                self.led_obj.led_output(task.name)


task_class_list=[ (mplayer.MPlayerTask, "aud"),
                  (netradio.NetRadioTask, "rad"),
                  (ip.IPTask, "IP"),
                  (cpu.CPUTask, "CPU"),
                  (conn.ConnTask, "Conn"),
]

class FakeIRReceiver:
    def __init__(self):
        self.fifo = constants.ir_fifo 
        self.reader = None
        self.writer = None
        self.fifo_created = self.create_fifo()
        if self.fifo_created:
            self.open_fifo()
        
    def create_fifo(self):        
        ret = False
        try:
            if not os.path.exists( self.fifo ): os.mkfifo(self.fifo)
            if not stat.S_ISFIFO(os.stat(self.fifo).st_mode):
                print "Fail to create fifo: ", self.fifo
            else:
                ret = True
        except Exception, e:
            print e
            pass
        return ret

    def open_fifo(self, flag="t", block=False):
        if not self.fifo_created : return False
        try:
            if block: mode = 0 
            else:     mode = os.O_NONBLOCK
            self.reader = os.open(self.fifo, os.O_RDONLY | mode )
            self.writer = os.open(self.fifo, os.O_WRONLY | mode )
        except Exception,e :
            print e

    def close(self):
        if self.reader: os.close(self.reader)
        if self.writer: os.close(self.writer)

    def read(self):
        msg = None
        if self.reader:
            msg = os.read(self.reader, 1024)
        return msg

    def write(self, msg): 
        if self.writer:
            os.write(self.writer, msg)
            return len(msg)
        else:
            return 0

    def select(self, t= 0, timeout = 0.01):
        inputs  = []
        outputs = []
        exceps  = []
        if t == 0: ## select read
            inputs = [self.reader]
        elif t == 1: ## select write
            outputs = [self.writer]
        else:
            return False
        readable, writable, exceptional = select.select(inputs, outputs, exceps, timeout)
        if not (readable or writable ):
            return False 
        else:
            return True
        
    def read_code(self, dev, timeout):
        ret = None
        if self.select(0, timeout):
            key_code = self.read()
            key_status = "released"
            try:
                key_code = int(key_code.strip().split("\n", 1)[0].split("\r", 1)[0])
                ret = (key_code, key_status)
            except Exception, e:
                print e
        return ret

def do_daemon(argv = None):
    iro   = ir.IRReceiver(ir.REMOTE_MODEL, REMOTE_CONF_FILE )
    ledui = led.create_ledui_object(True)
    main_task = MainTask('main', iro, ledui)
    main_task.register(0)
    main_task.start()
    i = 1
    for cls, name in task_class_list:
        o = cls(name)
        o.register(i)
        if i == 1:
            o.set_current()
        i += 1

    if RUNNING_MODE == constants.RUNNING_MODE_DEBUG:
        iro = FakeIRReceiver()
    while True:
        try:
            key = iro.read_code(None, 0.010)
            if key: 
                log.cblog("do_daemon: read key: %s" % key[0])
                main_task.put_key(key)
            task = main_task.get_current_task()         
            if task:
                if task.is_running():
                    output = task.get_output()
                    ledui.led_output(*output)
                else:
                    ledui.led_output(task.name)
                task.call_callback()
        except KeyboardInterrupt, e:
            ledui.stop()
            break
    ledui.join()        
    ledui.deinit_pins()
    pass

def do_play(argv):
    ##TODO
    pass

cmd_table = { "daemon"  : [do_daemon, 1, 1 ], 
              "play"    : [do_play, 1, 1 ], 
            }

def usage():
    print "cbplayer.py play"  
    print "cbplayer.py daemon"  
    sys.exit(0)

if __name__ ==  "__main__" :
    argv = sys.argv 
    argc = len(argv)
    argv.pop(0)
    argc -= 1
    if argc == 0: usage()
    cmd = argv[0]
    if cmd not in cmd_table: usage()
    max_param = cmd_table[cmd][2]
    min_param = cmd_table[cmd][1]
    if argc > max_param or argc < min_param : usage()
    cmd_table[cmd][0](argv[1:])
