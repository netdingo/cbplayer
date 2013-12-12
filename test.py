
import os
try:
    import fcntl
    import sh
except ImportError, e:
    pass
import re, Queue, time
import threading
import pdb

class MPlayerInteractiveObj():
    def __init__(self, out_iter):
        self.out_iter = out_iter
        self.stdin = None
        self.fifofile = "/var/mplayer_input"
        self.fifo_created = self.create_fifo()
        self.ready = False
        pass

    def get_fifo(self):
        return self.fifofile

    def create_fifo(self):
        if not os.path.exists(self.fifofile ):
            sh.mkfifo( self.fifofile )
        ret = True if os.path.exists(self.fifofile ) else False
        return ret

    def io_ready(self):
        return self.ready

    ## output callback
    def __call__(self, line, stdin, process):
        #print "output: ", line
        self.stdin = stdin
        if self.out_iter : self.out_iter(line) 
        self.ready = True
        pass

    def close(self):
        return 

    def write(self, s):
        ##print "write : ", s
        try:
            if self.fifo_created: 
                fd = open(self.fifofile, "a+t")
                fd.write(s)
                #sh.echo(s, ">", self.fifofile)
                fd.close()
        except Exception, e:
            print e
        pass


class Mplayer:
        #  Initializes this Mplayer with the specified Pymp.
        def __init__(self):
            self.in_out_obj = None
            self.proc  = None
            self.queryStatus = queryStatus
            self.proc = self.create_proc(queryStatus)
                
        def create_proc(self, queryStatus):
            self.in_out_obj = MPlayerInteractiveObj(queryStatus)
            ##self.proc = sh.mplayer("-slave", target, "2>/dev/null", _bg = True, _in = self.in_out_obj, _out = self.in_out_obj)
            ##self.proc = sh.mplayer("-slave", "-nolirc", "-quiet","-really-quiet",  "-msglevel statusline=6", "-msglevel global=6", "-idle", "-input", "file=%s" % self.in_out_obj.get_fifo(), "2>/dev/null", _bg = True, _out = self.in_out_obj)
            self.proc = sh.mplayer("-slave", "-nolirc", "-quiet", "-idle", "-input", "file=%s" % self.in_out_obj.get_fifo(), "2>/dev/null", _bg = True, _out = self.in_out_obj)
            return self.proc

        def ready(self):
            return self.in_out_obj.io_ready()

        #  Issues command to mplayer.
        def cmd(self, command):
            if self.in_out_obj == None:
                return
            try:
                self.in_out_obj.write(command + "\n")
            except StandardError:
                return

        def write(self, s):
            self.in_out_obj.write(s + "\n")

        def wait(self):
            if self.proc != None:
                self.proc.wait()
        #
        #   Plays the specified target.
        def play_1(self, target):
            self.in_out_obj = MPlayerInteractiveObj(self.queryStatus)
            ##self.proc = sh.mplayer("-slave", target, "2>/dev/null", _bg = True, _in = self.in_out_obj, _out = self.in_out_obj)
            ##self.proc = sh.mplayer("-slave", "-quiet", target,  _bg = True, _in = self.in_out_obj, _out = self.in_out_obj)
            ##self.proc = sh.mplayer("-slave", "-nolirc", "-quiet", "-idle", "-input", "file=%s" % self.in_out_obj.get_fifo(), "2>/dev/null", _bg = True, _in=self.in_out_obj, _out = self.in_out_obj)
            self.stopped = False 

        #   Plays the specified target.
        def play(self, target):
            self.stopped = False 
            self.cmd("loadfile %s" % target)

def queryStatus(line):
    print line
        
po = Mplayer()        
while not po.ready():
    time.sleep(1)
po.play("1.mp3")
while True:
    cmd = raw_input("input command: ")
    if cmd.strip() == 'exit':
        break
    po.cmd(cmd)
po.wait()
