#
# This file is part of Advene.
# 
# Advene is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# Advene is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Foobar; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""mplayer control class.

We reuse code from the pymp project :
http://jdolan.dyndns.org/jaydolan/pymp.html
"""

import os
try:
    import fcntl
    import sh
    import psutil
except ImportError, e:
    pass
import re, Queue, time, select, subprocess 
import threading
import pdb
from log import cblog
from constants import isLinux

STATUS_TIMEOUT = 50
normal_end = 1
force_end  = 4

# Dummy classes to match pymp API
class Control:
    def __init__(self):
        self.current_position_value=0
        
    def setProgress(self, time):
        self.current_position_value=time
        return

class Playlist(list):
    def __init__(self):
        self.continuous=True
        self.current_index=0

    def clear(self):
        self.current_index=0

    def get_item(self, increment = 1):        
        if self.current_index is None:
            self.current_index = 0
        else:
            self.current_index += increment 
        count = len(self)
        self.current_index = (self.current_index + count) % count
        if self.current_index >= count:
            #pdb.set_trace()
            pass
        try:
            n=self[self.current_index]
        except IndexError:
            return None
        return n

    def prev(self):
        return self.get_item(-1)

    def current(self):
        n=self[self.current_index]
        return n

    def next(self):
        return self.get_item(1)

    def get_current(self):
        return self.current_index

    def set_current(self, index):
        count = len(self) 
        if index >= count or index < 0:
            return False 
        self.current_index = index
        return True

class Pymp:
    def __init__(self):
        self.control=Control()
        self.playlist=Playlist()

    def get_song_count(self):
        return len(self.playlist) 

"""Dummy player interface
"""

class StreamInformation:
    def __init__(self):
        self.streamstatus=None
        self.url=""
        self.position=0
        self.length=0
        self.index=0
        
class PositionKeyNotSupported(Exception):
    pass

class PositionOrigin(Exception):
    pass

class InvalidPosition(Exception):
    pass

class PlaylistException(Exception):
    pass

class InternalException(Exception):
    pass

class Player:
    # Class attributes
    AbsolutePosition=0
    RelativePosition=1
    ModuloPosition=2

    ByteCount=0
    SampleCount=1
    MediaTime=2

    # Status
    PlayingStatus=0
    PauseStatus=1
    ForwardStatus=2
    BackwardStatus=3
    InitStatus=4
    NormalEndStatus=5
    ForceEndStatus=6
    StopStatus=7
    UndefinedStatus=8

    PositionKeyNotSupported=Exception()
    PositionOriginNotSupported=Exception()
    InvalidPosition=Exception()
    PlaylistException=Exception()
    InternalException=Exception()

    def __init__(self):
        self.status=Player.UndefinedStatus
        self.relative_position=0
        self.pymp=Pymp()
        self.end_key = False
        self.current_song = None
        self.song_count = 0
        self.song_lock = threading.Lock()
        self.mplayer=Mplayer(self.pymp)
        self.position_update()
        pass

    def get_song_count(self):
        return self.pymp.get_song_count()

    def get_current_song_index(self):
        return self.pymp.playlist.get_current()
                
    def is_playing(self):
        return self.status == Player.PlayingStatus

    def lock(self):
        self.song_lock.acquire()

    def unlock(self):
        self.song_lock.release()

    def is_force_end(self): ## one song end
        return self.status == Player.ForceEndStatus

    def is_normal_end(self): ## one song end
        return self.status == Player.NormalEndStatus

    def is_stopped(self): ## press stop key
        return self.status == Player.StopStatus

    def is_not_init(self):
        return self.status == Player.UndefinedStatus

    def check_status(self):
        self.lock()
        if self.is_normal_end():
            if self.song_count > 0 : self.play_next_song()
        self.unlock()
        self.mplayer.get_time_pos()
        #self.log( "check_status: self.status: %s, pos: %s" % (self.status, self.pymp.control.current_position_value ))

    def select_song(self, index):
        self.pymp.playlist.set_current(index)

    def dvd_uri(self, title=None, chapter=None):
        return "dvd://%s" % str(title)

    def log(self, *p):
        cblog("%s" % p)
        
    def get_media_position(self, origin, key):
        self.log("get_media_position")
        return long(self.pymp.control.current_position_value * 1000)

    def set_media_position(self, position):
        self.log("set_media_position %s" % str(position))
        self.mplayer.cmd("seek %d 2" % (position / 1000))
        return
    
    def start(self, position):
        self.log("start %s" % str(position))
        if self.song_count > 0:
            self.lock()
            song = self.pymp.playlist.current()
            self.play(song)
            self.unlock()
        return

    def play(self, song):
        self.log("play  %s" % song)
        self.current_song = song
        self.status = self.PlayingStatus ##TODO
        self.mplayer.play(song)
        
    def pause(self, position): 
        self.log("pause %s" % str(position))
        self.mplayer.pause()

    def resume(self, position):
        self.log("resume %s" % str(position))
        self.mplayer.pause()

    def handle_end_status(self, end_code):        
        if end_code == normal_end:
            self.status=Player.NormalEndStatus
        elif end_code == force_end:
            self.status=Player.ForceEndStatus
        else:
            #pdb.set_trace()
            pass
        #print "-->end_code : %d, status = %d" % (end_code, self.status)
        self.pymp.control.setProgress(-1)

    def end(self): 
        self.log("end..") 
        self.end_key = True
        end_code = self.mplayer.stop()
        self.handle_end_status(end_code)

    def stop(self, position): 
        self.log("stop %s" % str(position))
        self.end_key = False 
        end_code = self.mplayer.stop()
        self.handle_end_status(end_code)

    def prev(self, position):
        self.log("prev %s" % str(position))
        if len(self.pymp.playlist) > 0:
            ##self.stop(position)
            self.lock()
            prev_song = self.pymp.playlist.prev()
            self.play(prev_song)
            self.unlock()

    def next(self, position):
        self.log("next %s" % str(position))
        if len(self.pymp.playlist) > 0:
            ##self.stop(position)
            self.lock()
            next_song = self.pymp.playlist.next()
            self.play(next_song)
            self.unlock()

    #  Triggered when mplayer's stdout reaches EOF.
    def play_next_song(self ):
        if self.pymp.playlist.continuous:  #play next target
            next_song = self.pymp.playlist.next()
            #print "play_next_song: %s", next_song, ", eof: ", self.mplayer.eof
            self.play(next_song)
        else:  #reset progress bar
            self.pymp.control.setProgress(-1)
        return False

    def exit(self):
        self.log("exit")
        self.mplayer.close()
        self.pymp.control.setProgress(-1)  #reset bar
    
    def playlist_add_item(self, item):
        self.pymp.playlist.append(item)
        self.song_count += 1

    def playlist_clear(self):
        self.current_song = None
        self.end_key = False ## default is not stop key
        self.pymp.playlist.clear()
        self.pymp.control.setProgress(-1)
        self.mplayer.clear()
        self.status=Player.UndefinedStatus
        del self.pymp.playlist[:]
        self.song_count = 0
        
    def playlist_get_list(self):
        return self.pymp.playlist[:]

    def playlist_add_list(self, playlist):
        self.pymp.playlist.extend(playlist)
        self.song_count = len(self.pymp.playlist)

    def snapshot(self, position):
        self.log("snapshot %s" % str(position))
        self.mplayer.cmd("screenshot")
        return None

    def all_snapshots(self):
        self.log("all_snapshots %s")
        return [ None ]
    
    def display_text (self, message, begin, end):
        self.log("display_text %s" % str(message))
        self.mplayer.cmd("osd_show_text %s" % message)

    def get_stream_information(self):
        s=StreamInformation()
        if self.mplayer.in_out_obj != None:
            s.position=long(self.pymp.control.current_position_value * 1000)
            if self.mplayer.paused:
                self.status=self.PauseStatus
            elif self.mplayer.stopped > 0:
                self.handle_end_status(self.mplayer.stopped)
            """
            elif s.position > 0: ##TODO
                self.status=self.PlayingStatus
            else:
                self.status= self.UndefinedStatus
            """
            s.streamstatus=self.status
            s.length=long(self.mplayer.totalTime * 1000)
            s.index=self.pymp.playlist.get_current()
            try:
                if len(self.pymp.playlist) > 0: 
                    s.url=self.pymp.playlist.current()
                else:
                    s.url = ""
            except Exception, e:
                pass
        else:
            self.log("get_stream_information: no in_out_obj!" ) 
            s.streamstatus=self.status
            s.position=0
            s.length=0
            s.url=''
            s.index=0
            if self.pymp.playlist:
                s.url=self.pymp.playlist[0]
        return s

    def sound_get_volume(self):
        return 0

    def sound_set_volume(self, v):
        self.log("sound_set_volume %s" % str(v))

    # Helper methods
    def create_position (self, value=0, key=None, origin=None):
        """Create a Position.
        """
        return value

    def update_status (self, status=None, position=None):
        """Update the player status.

        Defined status:
           - C{start}
           - C{pause}
           - C{resume}
           - C{stop}
           - C{set}
           - C{prev}
           - C{next}

        If no status is given, it only updates the value of self.status

        If C{position} is None, it will be considered as zero for the
        "start" action, and as the current relative position for other
        actions.

        @param status: the new status
        @type status: string
        @param position: the position
        @type position: long
        """
        print "mplayer update_status %s" % status
        
        if status == "start" or status == "set":
            if position is None:
                position=0
            else:
                position=long(position)
            self.position_update()
            print "self.status: ", self.status
            if self.status in (self.NormalEndStatus, self.ForceEndStatus, self.StopStatus, self.UndefinedStatus):
                self.start(position)
            else:
                self.set_media_position(position)
        else:
            if position is None:
                position = 0
            else:
                position=long(position)

            if status == "pause":
                self.position_update()
                if self.status == self.PauseStatus:
                    self.resume (position)
                else:
                    self.pause(position)
            elif status == "resume":
                self.resume (position)
            elif status == "stop":
                self.stop (position)
            elif status == "end":
                self.end()
            elif status == "prev":
                self.prev(position)
            elif status == "next":
                self.next(position)
            elif status == "" or status == None:
                pass
            else:
                print "******* Error : unknown status %s in mplayer" % status
        self.position_update()

    def is_active(self):
        # FIXME: correctly implement this
        return True

    def check_player(self):
        # FIXME: correctly implement this
        print "check player"
        return True

    def position_update(self, ret_value = 0):
        s = self.get_stream_information ()
        self.status = s.streamstatus
        self.stream_duration = s.length
        self.current_position_value = s.position
        self.song_index = s.index
        if ret_value == 1:
            return ( s.url, self.status, s.length, self.current_position_value, self.song_index )

    def set_visual(self, xid):        
        self.mplayer.wid=xid
        return
    

class MPlayerInteractiveObj():
    def __init__(self, out_iter, fifofile):
        self.out_iter = out_iter
        self.stdin = None
        self.proc  = None
        self.fifofile = fifofile
        self.fifo_created = self.create_fifo(fifofile)
        self.ready = False
        pass

    def set_proc(self, proc):
        self.proc = proc

    def create_fifo(self, fifo):
        ret = True
        if isLinux:
            if not os.path.exists(fifo):
                sh.mkfifo( fifo )
            ret = True if os.path.exists(fifo) else False
        return ret

    def io_ready(self):
        return self.ready

    def get_fifo(self):
        return self.fifofile

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
        ret = False
        try:
            if self.fifo_created: 
                fd = open(self.fifofile, "a+t")
                fd.write(s)
                #sh.echo(s, ">", self.fifofile)
                fd.close()
                ret = True
        except Exception, e:
            print e
        return ret
        pass

#
#  Provides simple piped I/O to an mplayer process.
#
class Mplayer:
        #  Initializes this Mplayer with the specified Pymp.
        def __init__(self, pymp):
            self.re_time=re.compile("(A|V):\s*(\d+\.\d+)")
            self.re_length=re.compile("ANS_LENGTH=(\d+)")
            self.re_time_pos=re.compile("ANS_TIME_POSITION=(\d+)")
            self.re_eof = re.compile("\s*EOF code: (\d+)")
            self.paused=False
            self.stopped = -1
            self.totalTime=0
            self.wid=None
            self.pymp = pymp
            self.in_out_obj = None
            self.fifofile = "/var/mplayer_input"
            self.create_proc()
            self.current_song = None

        def create_mplayer(self, ioobj):
            if isLinux:
                proc = sh.mplayer("-slave", "-nolirc", "-quiet", "-idle", "-input", "file=%s" % self.fifofile, "2>/dev/null", _bg=True, _out = self.in_out_obj, _encoding = 'gbk')
                print "create_mplayer: pid = ", proc.pid
            else:
                proc = None
            ioobj.set_proc(proc)

        def mplayer_exists(self):            
            try:
                ret = False
                if self.in_out_obj == None : return ret
                ret = psutil.pid_exists(self.in_out_obj.proc.pid)
            except Exception, e:
                print e
            return ret

        def create_proc(self):
            ##self.proc = sh.mplayer("-slave", target, "2>/dev/null", _bg = True, _in = self.in_out_obj, _out = self.in_out_obj)
            #self.proc = sh.mplayer("-slave", "-nolirc", "-quiet", "-idle", "-input", "file=%s" % self.in_out_obj.get_fifo(), "2>/dev/null", _bg = True, _out = self.in_out_obj, )
            self.in_out_obj = MPlayerInteractiveObj(self.parse_mplayer_output, self.fifofile)
            self.create_mplayer(self.in_out_obj)
            timeout = time.time() + 4.0 
            while time.time() < timeout and not self.mplayer_exists():
                time.sleep(0.2)
            if not self.mplayer_exists():
                cblog("Fail to create mplayer!" )
            else:
                time.sleep(1)
            """
            count = 0
            while not self.in_out_obj.io_ready():
                time.sleep(0.2)
                count += 1
                if count > 50:
                    print "Fail to start mplayer process!"
                    return None
            """
            return self.in_out_obj

        def ready(self):
            return self.in_out_obj.io_ready()

        def clear(self):
            self.paused=False
            self.stopped = -1
            self.totalTime=0
            self.wid=None
            self.current_song = None
        
        #   Plays the specified target.
        def play(self, target):
            if not self.mplayer_exists():
                self.create_proc()
            else:
                self.stopped = self.wait_for_stop()
            self.clear()
            if False == self.cmd("loadfile \"%s\"" % target):
                self.current_song = target
            self.stopped = -1

        def get_time_pos(self):                
            self.cmd("get_time_pos") #grab time position

        def query_status(self, song):
            #print "query_status song : ", song
            #print "query_status current_song: ", self.current_song 
            return  self.stopped
        #
        #  Issues command to mplayer.
        def cmd(self, command):
            ret = False
            if self.in_out_obj == None:
                return ret
            try:
                ret = self.in_out_obj.write(command + "\n")
            except Exception, e:
                print e
                pass
            return ret

        def volume(self, vol):
            self.cmd("volume %s", ) #set the soft volume
        #
        #  Toggles pausing of the current mplayer job and status query.
        def pause(self):
            """
            if self.in_out_obj == None:
                return
            """
            if self.paused:  #unpause       
                self.startStatusQuery()
                self.paused = False
            else:  #pause
                self.stopStatusQuery()
                self.paused = True
            self.cmd("pause")

        def stop(self):
            if self.stopped == -1:  # not stopped
                self.stopStatusQuery()
                self.cmd("stop")
            self.stopped = self.wait_for_stop()
            if self.stopped == -1:
                self.clear()
            return self.stopped 

        def wait_for_stop(self):
            max_count = 20 ## seconds waiting for stop
            count = 0
            while self.stopped == -1 and count < max_count:
                time.sleep(0.1)
                count += 1
            if count >= max_count: 
                self.stopped = -1
            return self.stopped
        
        #  Cleanly closes any IPC resources to mplayer.
        def close(self):
            if self.paused:  #untoggle pause to cleanly quit
                self.pause()
            self.stopStatusQuery()  #cancel query
            self.stopEofHandler()  #cancel eof monitor
            self.cmd("quit")  #ask mplayer to quit
            self.stopped = self.wait_for_stop()
            try:                    
                self.in_out_obj.close()   #close pipes
            except StandardError:
                pass
            self.in_out_obj = None

         #  Queries mplayer's playback status and upates the progress bar.
        def parse_mplayer_output(self, line):                                          
            """
              TIPS: workaround for dectecting end of file:
              1) add the following lines in /etc/mplayer/mplayer.conf:
                really-quiet=1
                msglevel=statusline=6
                msglevel=global=6
              2) in this function, monitor line output for the string like below:
                  EOF code: 1
            """
            curTime = None
            try:  #attempt to fetch last line of output
                # If totalTime is not yet known, look for it
                if self.totalTime == 0:
                    m=self.re_length.search(line)
                    if m:
                        self.totalTime = long(m.group(1))
                        print "Got length: %d" % self.totalTime
                
                m=self.re_time_pos.match(line)
                if m:
                    curTime = float(m.group(1))
                else:
                    print line
                m=self.re_eof.match(line)
                if m : 
                    end_code = int(m.group(1))
                    cblog("song come to end, self.stopped = %d" % end_code)
                    self.stopped = end_code 
            except StandardError:
                pass 
            if curTime:
                self.pymp.control.setProgress(curTime) #update progressbar
                if self.totalTime == 0:
                    #print "Getting time length"
                    self.cmd("get_time_length") #grab the length of the file
            return True
        #
        #  Removes the status query monitor.
        def stopStatusQuery(self):
            pass
        #
        #  Removes the EOF monitor.
        def stopEofHandler(self):
            pass
        #
        #  Inserts the status query monitor.
        #
        def startStatusQuery(self):
            pass
        #
        #  Inserts the EOF monitor.
        def startEofHandler(self):
            pass
        
#End of file
