## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard net radio module, which plays on-line radio
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time, threading, re
try:
    import fcntl
    import sh
except ImportError, e:
    pass
import pymp
import cbtask, ir, mplayer
from   constants import *
from   led import led_format_string 
from   log import cblog
import pdb


class NetRadioTask(mplayer.MPlayerTask):
    def __init__(self, name):
        mplayer.MPlayerTask.__init__(self, name)
        self.radio_list = None
        self.exit = False
        self.digit_select = -1
        self.digit_select_time = None
        self.volume = 50 ## 50%

    def main(self): ## task entry 
        global local_dir 
        ret = 0 
        self.stop_player("aud")
        self.viewer.show_boot_sign("r--2")
        mplayer.load_media_driver()                
        self.viewer.show_boot_sign("r--1")
        ro = RadioListFile(RADIO_CONF)
        self.radio_list = ro.get_radio_list()
        self.viewer.show_boot_sign("b--0", 4)
        self.handle_dvd_play_key()
        position = 0
        while not self.exit:
            if self.player.is_playing():
                url, status, length, position, radio_index = self.player.position_update(1)
                self.viewer.show_position( status, radio_index, length, position ) 
            else:
                position = 0
            self.player.check_status()
            time.sleep(1)
            self.test_pos = position
        ret = 0
        return ret 

    def update_radio_list(self):
        self.player.update_status("end")
        self.player.playlist_clear()
        #print "add new play list: ", self.radio_list 
        self.player.playlist_add_list( self.radio_list )
        self.player.update_status("start")

    def handle_dvd_play_key(self): ##
        self.set_volume()
        select_idx = self.digit_key_timeout(1)
        if select_idx >=0 : 
            if select_idx < len(self.radio_list): 
                self.play_song(select_idx)
            else:
                return
        elif self.player.is_stopped() or self.player.is_force_end():
            current_idx = self.player.get_current_song_index()
            self.log("handle_dvd_play_key: continue play radio_index: %s, player status: %s" % (current_idx, self.player.status))
            self.player.update_status("start")
        else:
            self.update_radio_list()
        current_idx = self.player.get_current_song_index()
        self.viewer.show_song_dir(current_idx, 3, "r")

    def handle_left_key(self): ##
        pass
    def handle_right_key(self): ##
        pass
    def handle_dvd_forward_key(self): ##
        pass
    def handle_dvd_backward_key(self): ##
        pass

class RadioListFile(list):
    """
       radio list structure:
         [ [ sect_name1,[ [ name1, status1, url1 ], 
                          [ name2, status2, url2 ], 
                          [ name3, status3, url3 ], 
                          ...
                        ]
           ...
         ]
    """
    unknown_type = -1
    section_type = 0
    value_type   = 1
    def __init__(self, fn):
        self.fn = fn
        self.re_section = re.compile("\[(.*)\]")
        self.re_value   = re.compile("name\s*=\s*(.*)\|(.*)\|(.*)$")
        self.proto_fmt  = re.compile("\s*(.*)://\s*(.*)$")
        self.load()

    def strip_comment(self, line, comment_char="#"):
        while True:
            if not line or line.strip() == "" : return None 
            idx = line.strip().find(comment_char)
            if idx >= 0:
                line = line[:idx].strip()
                continue
            break
        return line

    def is_section(self, line):
        m=self.re_section.search(line)
        return m.group(1) if m else None

    def is_value(self, line):
        m=self.re_value.search(line)
        if not m : return None
        return [ m.group(1), m.group(2), m.group(3) ]

    def format_value(self, name, status, url):
        return "name = %s |%s|%s\n" % (name, status, url)

    def parse_line(self, line):
        ret = None
        line = self.strip_comment(line)        
        if not line : return ret
        o = self.is_section(line)
        if o: 
            return [ RadioListFile.section_type, o ]
        else:
            o = self.is_value(line)
            if o : 
                return [ RadioListFile.value_type, o ] 
            else:
                return ret

    def load(self):
        try:
            fd = None
            fd = open(self.fn, "rt")
            radio_section = None
            radio_list = []
            for line in fd:
                ret = self.parse_line(line)
                if not ret : continue
                line_type, o = ret
                if line_type == RadioListFile.section_type:
                    if radio_section :
                        self.append( [ radio_section, radio_list ] ) 
                    radio_list = []
                    radio_section = o
                elif line_type == RadioListFile.value_type:
                    name, status, url = o
                    radio_list.append( o )
            if radio_section :
                self.append( [ radio_section, radio_list ] )
        except Exception, e:
            print "load exception: ", e
        finally:
            if fd: fd.close()
            return
        pass

    def save(self):
        try:
            fd = None
            fd = open(self.fn, "w+t")
            radio_section = None
            for sect_name, lists in self:
                fd.write("[%s]\n" % sect_name)
                idx = 0
                for item in lists:
                    name, status, url = item
                    line = self.format_value(name, str(status), url)
                    fd.write(line)
                fd.write("\n")
        except Exception, e:
            print "save exception: ", e
        finally:
            if fd: fd.close()
            return
        pass

    def remove_newline(self, url):
        url = url.split("\r", 1)[0]
        return url.split("\n", 1)[0]

    def get_real_url(self, url):
        ret = None
        m = self.proto_fmt.search(url)
        if m:
            proto = m.group(1).strip().lower()
            if proto == 'file':
                value = m.group(2).strip()
                exists = False
                i = 0
                while i < 2:
                    if not os.path.exists(value):
                        value = os.path.join(prog_home, value)
                        i += 1
                        continue
                    else:
                        exists = True
                        break
                if exists : 
                    ret = []
                    try:
                        for line in sh.sh(value): ## exec the script
                            line = self.remove_newline(line) 
                            if line: ret.append( line )
                    except Exception, e:
                        cblog("get_real_url: exception" + repr(e))
                        print e
            else:
                ret = url
        return ret

    def get_radio_list(self, available = 1):
        ret = []
        for sect_name, lists in self:
            for item in lists:
                name, status, url = item
                if status.strip() == "1" : ## radio is available 
                    url = self.get_real_url(self.remove_newline(url))
                    if isinstance(url, list):
                        for item in url:
                            if item: ret.append(item)
                    else:
                        if url: ret.append(url)
        return ret

class RadioList:
    def __init__(self, conf):
        self.conf = conf
        self.player = pymp.Player()
        self.radio_list = RadioListFile(conf)

    def check_status(self):
        timeout = time.time() + 20.0
        position = 0
        while  time.time() < timeout:
            url, status, length, position, radio_index = self.player.position_update(1)
            self.player.check_status()
            time.sleep(1)
        if position > 0: 
            return True
        else:
            return False

    def play_radio(self, url):
        ret = False
        url = self.radio_list.remove_newline(url)
        self.player.play(url)
        ret = self.check_status()
        return ret

    def verify_radio_connection(self):
        for sect_name, lists in self.radio_list:
            idx = 0
            for item in lists:
                name, status, url = item
                if self.play_radio(url) == True:
                    lists[idx][1] = 1
                else:
                    lists[idx][1] = 0
                idx += 1
        self.radio_list.save()

def check_radio_connection(conf):        
    rl = RadioList(conf)
    rl.verify_radio_connection()

if __name__ ==  "__main__" :
    argv = sys.argv
    argc = len(argv)
    if argc > 1:
        conf = argv[1]
        check_radio_connection(conf)
    pass
