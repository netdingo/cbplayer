## encoding=utf-8
#!/usr/bin/env python
"""
  ir module, which monitor /dev/input/event1 device to get key event from remote
Note: currently, only support LG_MKJ32022805 remote
export those following function:

"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time, select
try:
    import sh
except ImportError, e:
    pass
import pdb

IR_MODULE = "sun4i-ir"
REMOTE_MODEL = "LG_MKJ32022805"

key_table = { REMOTE_MODEL : {'pktlen':32, 'keyaddr': 10, 'pressed': 12  }, 
            }

digital_key = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')

class KeyConf:
    def __init__(self, conf_file):
        self.conf_file = conf_file
        self.key_conf = self.load_key_conf()

    def save_key_name(self, key_code):
        while True:
            name = raw_input("Input key name:")
            name = name.lower()
            if name == "--exit--":
                return 1
            if not self._verify_key_name(name) : 
                print "invalid name, please reenter a new key name."
                continue
            self.key_conf[name] = key_code
            break
        return 0 

    def _verify_key_name(self, name):
        invalid_char_count = reduce(lambda x, y: x if y.isalpha() or y.isdigit() or y == '-' or y == '_' else x + 1, name, 0) 
        if invalid_char_count > 0:
            return False
        else:
            return True

    def _open_file(self, fn, mode = "rt", create = False):
        if not create and not os.path.exists(fn):
            return None
        try:
            fp = open(fn, mode)
        except Exception, e:
            fp = None
        return fp

    def load_key_conf(self):
        """
          remote key conf file format:
             KEY_NAME  key_code
        """
        conf = {}
        fp = self._open_file(self.conf_file)
        if not fp : return conf
        for line in fp:
            line = line.strip()
            if line.startswith("#") : continue
            items = line.split()
            if len(items) != 2 : continue
            conf[items[0]] = items[1]
        fp.close()
        return conf

    def save_key_conf(self):
        fp = self._open_file(self.conf_file, "wt", create = True)
        if not fp : return False
        for name, code in self.key_conf.items():
            fp.write("%s %s\n" % (name, code))
        fp.close()
        pass 

    def get_key_dict(self):
        key_dict = {}
        for name, key in self.key_conf.items():
            try:
                key = int(key)
                key_dict[key] = name
            except Exception, e:
                continue
                pass
        return key_dict

class IRReceiver:
    def __init__(self, model, key_conf_file):
        global key_table
        self.model = model
        self.key_conf_file = key_conf_file
        self.key_conf = KeyConf(self.key_conf_file)
        self.dev = self.ir_init() 
        if self.model not in key_table:
            print "unsupported remote model!"
        else:
            tbl = key_table[self.model] 
            self.pktlen  = tbl['pktlen']
            self.keyaddr = tbl['keyaddr']
            self.status  = tbl['pressed']
        if self.dev:
            self.devfp  = self._open_dev(self.dev)

    def get_key_dict(self):
        return self.key_conf.get_key_dict()

    def ir_get_dev(self):
        """
            get real ir device.
        """
        try:
            out = sh.grep(sh.dmesg(), IR_MODULE, _iter = True) 
            count = len(out) 
            if count > 0 and out.exit_code == 0:
                lines = filter(lambda x : x, out.stdout.split("\n"))
                last_line = lines[-1].split(IR_MODULE + " as")
                if len(last_line) > 1:
                    path = "/sys" + last_line[-1].strip() + "/event1/uevent"
                    out = sh.grep("DEVNAME", path, _iter = True) 
                    if out > 0 and out.exit_code == 0:
                        lines = filter(lambda x : x, out.stdout.split("\n"))
                        last_line = lines[-1].split("=")
                        if len(last_line) > 1:
                            dev = "/dev/" + last_line[-1].strip()
                            return dev
            return None
        except Exception, e:
            return None
        pass

    def ir_init(self):
        """
            check and load ir module and return real ir device.
        """
        dev = self.ir_get_dev()
        if dev == None:
            try:
                sh.modprobe(IR_MODULE)
                dev = self.ir_get_dev()
                return dev
            except Exception, e:
                return None
        else: ## has found right dev
            return dev

    def ir_deinit(self):
        #TODO
        pass

    def _open_dev(self, dev):
        fp = None
        try:
            if dev:
                fp = open(dev, "rb")
        except Exception, e:
            print "Fail to open device: ", dev
        return fp

    def _close_dev(self, fp):
        if fp: fp.close()

    def read_code(self, devfp = None, timeout=0.1):
        try:
            if devfp == None:
                fp = self.devfp
            else:
                fp = devfp
            if not fp : return None
            inputs  = [fp]
            outputs = []
            readable, writable, exceptional = select.select(inputs, outputs, inputs, timeout)
            if not (readable or writable or exceptional) :
                return None
            for h in readable:
                if h == fp:
                    keydata = fp.read(self.pktlen)
                    key_code, key_status, status_str = self._decode_key(keydata)  
                    ##self._dump_key(keydata, status_str)
                    if key_status == 0: ## key released
                        return (key_code, key_status)
            return None
        except Exception, e:
            return None
        pass

    def _decode_key(self, keydata):        
        key_code    = ord(keydata[self.keyaddr])
        key_status  = ord(keydata[self.status])
        if key_status == 1: 
            head = 'pressed '
        else:
            head = 'released'
        return (key_code, key_status, head)

    def _dump_key(self, keydata, status_string):
        ascii_list = map(lambda x: "%02X" % ord(x), keydata)
        print status_string, ":  ", " ".join(ascii_list)
        print "-" * 30

    def record(self):
        fp = self._open_dev(self.dev)
        exit = 0
        while True:
            keydata = fp.read(self.pktlen)
            key_code, key_status, status_str = self._decode_key(keydata)  
            self._dump_key(keydata, status_str)
            if key_status == 0: ## key released
                exit = self.key_conf.save_key_name(key_code) 
                if exit == 1: break
        self.key_conf.save_key_conf()
        self._close_dev(fp)
        pass

    def exit_read(self):        
        if self.devfp: self._close_dev(devfp)
        self.ir_deinit()
        pass

def read_key():
    iro = IRReceiver(REMOTE_MODEL, "lg_remote.conf")
    fp = iro._open_dev(iro.dev)
    key_code, key_status = iro.read_code(fp, timeout=0.2)
    ##iro._dump_key(keydata, status_str)
    if key_status == 0: ## key released
        return (key_code, key_status)
    iro._close_dev(fp)

def record_key():        
    iro = IRReceiver(REMOTE_MODEL, "lg_remote.conf")
    iro.record()

if __name__ ==  "__main__" :
    pass 
